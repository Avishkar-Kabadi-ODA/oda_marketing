# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from oda_marketing.oda_marketing.ai_engine.evaluator_agent import (
    EvaluationError,
    publish_stream_event,
)
from oda_marketing.oda_marketing.ai_engine.prompt_subagent import generate_dynamic_system_prompt

ACTIVE_STATUSES = ("Queued", "In Progress")
ENQUEUE_QUEUE = "long"
ENQUEUE_TIMEOUT_SECONDS = 600
GENERIC_FAILURE_MESSAGE = "AI Copilot evaluation failed. Please try again or contact an administrator."
STALE_REVIEW_MINUTES = 30


def enqueue_ai_review(docname, review_type="Writer", reviewer_instructions=None, requested_by=None):
    """Queue a review as a background job. Callers must have done their permission checks.

    Rejects the request while a review is already queued or running for the item.
    """
    status = frappe.db.get_value("Content Item", docname, "ai_review_status")
    if status in ACTIVE_STATUSES:
        frappe.throw(
            _("An AI review is already queued or running for this item. Please wait for it to finish."),
            frappe.ValidationError,
        )

    job_token = frappe.generate_hash(length=24)
    frappe.db.set_value(
        "Content Item",
        docname,
        {
            "ai_review_status": "Queued",
            "ai_review_error": None,
            "ai_review_started_on": frappe.utils.now_datetime(),
            "ai_review_job_token": job_token,
        },
        update_modified=False,
    )

    def enqueue_after_commit():
        try:
            frappe.enqueue(
                "oda_marketing.oda_marketing.ai_engine.runner.run_ai_review",
                queue=ENQUEUE_QUEUE,
                timeout=ENQUEUE_TIMEOUT_SECONDS,
                docname=docname,
                job_token=job_token,
                reviewer_instructions=reviewer_instructions,
                review_type=review_type,
                requested_by=requested_by,
            )
        except Exception as exc:
            frappe.db.set_value(
                "Content Item",
                docname,
                {
                    "ai_review_status": "Failed",
                    "ai_review_error": _("The background worker could not queue this review. Please try again."),
                    "ai_review_started_on": None,
                    "ai_review_job_token": None,
                },
                update_modified=False,
            )
            frappe.log_error(
                title="AI Copilot enqueue failed",
                message=f"Content Item {docname}: {type(exc).__name__}",
            )
            if not frappe.flags.in_test:
                frappe.db.commit()
            publish_stream_event(
                docname,
                requested_by,
                f"AI Copilot evaluation failed: {GENERIC_FAILURE_MESSAGE}",
                progress=0,
            )
            raise

    frappe.db.after_commit.add(enqueue_after_commit)


def run_ai_review(docname, reviewer_instructions=None, review_type="Writer", requested_by=None, job_token=None):
    """
    Background job (queued by enqueue_ai_review):
    1. Checks the usage limit.
    2. Invokes the Subagent to generate the dynamic system prompt.
    3. Invokes the Evaluator to score the deliverable.
    4. Updates Content Item fields and records an audit entry.
    A failed evaluation sets ai_review_status = "Failed" and records no review row.
    Does NOT change the workflow state: the score is informational only.
    """
    if not frappe.db.exists("Content Item", docname):
        return

    doc = frappe.get_doc("Content Item", docname)
    if not frappe.flags.in_test and (
        not job_token or job_token != getattr(doc, "ai_review_job_token", None)
    ):
        return

    notify_user = requested_by or doc.assigned_to or doc.owner

    settings = frappe.get_single("Marketing Settings")
    if review_type == "Reviewer":
        max_reviews = int(getattr(settings, "max_reviewer_copilot_reviews_per_item", 2) or 2)
    else:
        max_reviews = int(getattr(settings, "max_writer_copilot_reviews_per_item", 2) or 2)
    current_count = len([r for r in (doc.ai_reviews or []) if r.get("review_type") == review_type])

    if current_count >= max_reviews:
        restored = "Completed" if doc.ai_reviews else "Not Started"
        doc.db_set(
            {
                "ai_review_status": restored,
                "ai_review_error": None,
                "ai_review_started_on": None,
                "ai_review_job_token": None,
            },
            update_modified=False,
        )
        frappe.throw(
            _("Copilot review limit reached ({0}/{1}). No additional AI reviews can be triggered for this item.").format(
                current_count, max_reviews
            ),
            frappe.ValidationError,
        )

    frappe.flags.in_ai_copilot_review = True

    try:
        doc.db_set(
            {
                "ai_review_status": "In Progress",
                "ai_review_started_on": frappe.utils.now_datetime(),
            },
            update_modified=False,
        )
        publish_stream_event(docname, notify_user, "Stage 1: Generating the evaluation prompt...", progress=10)

        dynamic_prompt = generate_dynamic_system_prompt(doc, reviewer_instructions=reviewer_instructions)
        doc.db_set("ai_generated_prompt", dynamic_prompt, update_modified=False)

        publish_stream_event(docname, notify_user, "Stage 2: Evaluating content...", progress=30)

        # Imported here so tests can patch evaluate_content_item on this module if needed.
        from oda_marketing.oda_marketing.ai_engine.evaluator_agent import evaluate_content_item

        eval_res = evaluate_content_item(
            doc, dynamic_prompt, user_email=notify_user, reviewer_instructions=reviewer_instructions
        )

        score = int(eval_res["overall_score"])
        feedback = eval_res.get("ai_copilot_feedback", "")
        passing_score = int(getattr(settings, "ai_copilot_passing_score", 80) or 80)

        doc.ai_score = score
        doc.ai_review_status = "Completed"
        doc.ai_review_error = None
        doc.ai_review_started_on = None
        doc.ai_review_job_token = None
        doc.ai_generated_prompt = dynamic_prompt
        doc.ai_copilot_feedback = feedback

        if review_type == "Reviewer":
            doc.reviewer_copilot_feedback = feedback
        else:
            doc.writer_copilot_feedback = feedback

        verdict_label = "Passed" if score >= passing_score else "Revision Required"
        doc.append(
            "ai_reviews",
            {
                "review_datetime": frappe.utils.now_datetime(),
                "review_type": review_type,
                "score": score,
                "status": verdict_label,
                "feedback": feedback,
                "system_prompt": dynamic_prompt,
            },
        )

        doc.flags.ignore_permissions = True
        doc.flags.ignore_workflow = True
        doc.flags.ignore_validate = True
        doc.save(ignore_permissions=True)
        if not frappe.flags.in_test:
            frappe.db.commit()

        publish_stream_event(
            docname,
            notify_user,
            f"AI Score: {score}% (threshold: {passing_score}%). Review complete. The score is informational.",
            progress=100,
        )

    except Exception as exc:
        frappe.log_error(
            title="AI Copilot review failed",
            message=f"Content Item {docname}: {type(exc).__name__}",
        )
        frappe.db.set_value(
            "Content Item",
            docname,
            {
                "ai_review_status": "Failed",
                "ai_review_started_on": None,
                "ai_review_job_token": None,
            },
            update_modified=False,
        )
        if not frappe.flags.in_test:
            frappe.db.commit()
        shown = str(exc) if isinstance(exc, EvaluationError) else GENERIC_FAILURE_MESSAGE
        frappe.db.set_value(
            "Content Item",
            docname,
            "ai_review_error",
            shown,
            update_modified=False,
        )
        publish_stream_event(docname, notify_user, f"AI Copilot evaluation failed: {shown}", progress=0)
    finally:
        frappe.flags.in_ai_copilot_review = False


def recover_stale_ai_reviews():
    """Mark reviews without a live worker as Failed so users can retry."""
    cutoff = frappe.utils.add_to_date(
        frappe.utils.now_datetime(),
        minutes=-STALE_REVIEW_MINUTES,
    )
    last_name = ""
    while True:
        filters = {"ai_review_status": ["in", list(ACTIVE_STATUSES)]}
        if last_name:
            filters["name"] = [">", last_name]
        items = frappe.get_all(
            "Content Item",
            filters=filters,
            fields=["name", "ai_review_started_on", "modified", "assigned_to", "owner"],
            order_by="name asc",
            limit_page_length=200,
        )
        if not items:
            return

        for item in items:
            last_name = item.name
            started_on = item.ai_review_started_on or item.modified
            if not started_on or frappe.utils.get_datetime(started_on) > cutoff:
                continue
            frappe.db.set_value(
                "Content Item",
                item.name,
                {
                    "ai_review_status": "Failed",
                    "ai_review_error": _("Review timed out before completion. You can retry the review."),
                    "ai_review_started_on": None,
                    "ai_review_job_token": None,
                },
                update_modified=False,
            )
            publish_stream_event(
                item.name,
                item.assigned_to or item.owner,
                "AI Copilot review timed out before completion. You can retry the review.",
                progress=0,
            )