# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from oda_marketing.oda_marketing.ai_engine.prompt_subagent import generate_dynamic_system_prompt
from oda_marketing.oda_marketing.ai_engine.evaluator_agent import evaluate_content_item, publish_stream_event


def run_ai_review(docname, reviewer_instructions=None):
	"""
	Background job orchestrator (frappe.enqueue):
	1. Checks usage limit (max_copilot_reviews_per_item).
	2. Invokes Subagent to generate dynamic system prompt.
	3. Invokes Primary Evaluator Agent to score the deliverable.
	4. Updates Content Item fields and records audit entry.
	Note: Does NOT auto-transition workflow state — score is informational only.
	"""
	if not frappe.db.exists("Content Item", docname):
		return

	doc = frappe.get_doc("Content Item", docname)

	# Check usage limit before starting review
	settings = frappe.get_single("Marketing Settings")
	max_reviews = int(getattr(settings, "max_copilot_reviews_per_item", 3) or 3)
	current_count = len(doc.ai_reviews or [])
	if current_count >= max_reviews:
		frappe.throw(
			_("Copilot review limit reached ({0}/{1}). No additional AI reviews can be triggered for this item.").format(current_count, max_reviews),
			frappe.ValidationError
		)

	frappe.flags.in_ai_copilot_review = True

	try:

		# Mark status as In Progress
		doc.db_set("ai_review_status", "In Progress", update_modified=False)

		assigned_user = doc.assigned_to or doc.owner
		publish_stream_event(docname, assigned_user, "Stage 1: Triggering Prompt Generator Subagent...", progress=10)

		# Stage 1: Generate dynamic system prompt via Subagent
		dynamic_prompt = generate_dynamic_system_prompt(doc, reviewer_instructions=reviewer_instructions)
		doc.db_set("ai_generated_prompt", dynamic_prompt, update_modified=False)

		publish_stream_event(docname, assigned_user, "Stage 2: Evaluating content with dynamic system prompt...", progress=30)

		# Stage 2: Evaluate document via Primary Agent
		eval_res = evaluate_content_item(doc, dynamic_prompt, user_email=assigned_user, reviewer_instructions=reviewer_instructions)

		score = int(eval_res.get("overall_score", 0))
		feedback = eval_res.get("ai_copilot_feedback", "")

		passing_score = int(getattr(settings, "ai_copilot_passing_score", 80) or 80)

		# Update AI fields on Content Item
		doc.ai_score = score
		doc.ai_review_status = "Completed"
		doc.ai_generated_prompt = dynamic_prompt
		doc.ai_copilot_feedback = feedback

		# Record entry in AI Review History Table
		verdict_label = "Passed" if score >= passing_score else "Revision Required"
		doc.append("ai_reviews", {
			"review_datetime": frappe.utils.now_datetime(),
			"score": score,
			"status": verdict_label,
			"feedback": feedback,
			"system_prompt": dynamic_prompt
		})

		publish_stream_event(
			docname, assigned_user,
			f"AI Score: {score}% (threshold: {passing_score}%). Review complete — score is informational.",
			progress=100
		)

		doc.db_set({
			"ai_score": score,
			"ai_review_status": "Completed",
			"ai_generated_prompt": dynamic_prompt,
			"ai_copilot_feedback": feedback,
		}, update_modified=False)

		doc.flags.ignore_permissions = True
		doc.flags.ignore_workflow = True
		doc.flags.ignore_validate = True
		doc.save(ignore_permissions=True)

		# Send email notification to writer when AI score fails threshold
		if score < passing_score:
			notify_writer_copilot_failed(doc, score, feedback)

		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"AI Copilot Review failed for Content Item {docname}: {str(e)}")
		frappe.db.set_value("Content Item", docname, "ai_review_status", "Failed", update_modified=False)
		publish_stream_event(docname, None, f"AI Copilot Evaluation failed: {str(e)}", progress=0)
	finally:
		frappe.flags.in_ai_copilot_review = False


def notify_writer_copilot_failed(doc, score, feedback):
	"""Sends an automated alert to Content Writer when AI Copilot score is below threshold."""
	settings = frappe.get_single("Marketing Settings")
	if not settings.enable_email_notifications:
		return

	if not doc.assigned_to:
		return

	try:
		item_url = doc.get_template_context().get("content_item_url")
		subject = f"[COPILOT REVISION REQUIRED] Deliverable '{doc.title}' AI Quality Score: {score}%"
		message = f"""<p>Hello <b>{doc.get_user_full_name(doc.assigned_to)}</b>,</p>
<p>Your content deliverable <b>{doc.title}</b> has been evaluated by the <b>Marketing Copilot Agent</b>.</p>
<p><b>AI Quality Score:</b> <span style="color: #dc2626; font-weight: bold;">{score}%</span></p>
<p>The AI Copilot recommends revisions. Please review the feedback below, update your content draft, and resubmit when ready.</p>
<div style="background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 15px; margin: 15px 0;">
  {feedback}
</div>
<div style="margin-top: 15px;">
  <a href="{item_url}" target="_blank" style="display: inline-block; background-color: #4F46E5; color: #ffffff; padding: 10px 18px; text-decoration: none; border-radius: 6px; font-weight: 600;">View Content Item in Desk</a>
</div>"""
		frappe.sendmail(
			recipients=[doc.assigned_to],
			subject=subject,
			message=message,
			now=False
		)
	except Exception as e:
		frappe.log_error(f"Failed to send Copilot failure notification email for {doc.name}: {str(e)}")
