# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from oda_marketing.oda_marketing.ai_engine.prompt_subagent import generate_dynamic_system_prompt
from oda_marketing.oda_marketing.ai_engine.evaluator_agent import evaluate_content_item, publish_stream_event


def run_ai_review(docname, reviewer_instructions=None, review_type="Writer"):
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
	if review_type == "Reviewer":
		max_reviews = int(getattr(settings, "max_reviewer_copilot_reviews_per_item", 2) or 2)
		current_count = len([r for r in (doc.ai_reviews or []) if r.get("review_type") == "Reviewer"])
	else:
		max_reviews = int(getattr(settings, "max_writer_copilot_reviews_per_item", 2) or 2)
		current_count = len([r for r in (doc.ai_reviews or []) if r.get("review_type") == "Writer"])
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

		print(f"\n🚀 [AI COPILOT JOB STARTED] Deliverable: {docname} | Review Type: {review_type} | User: {assigned_user}", flush=True)

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

		if review_type == "Reviewer":
			doc.reviewer_copilot_feedback = feedback
		else:
			doc.writer_copilot_feedback = feedback

		# Record entry in AI Review History Table
		verdict_label = "Passed" if score >= passing_score else "Revision Required"
		doc.append("ai_reviews", {
			"review_datetime": frappe.utils.now_datetime(),
			"review_type": review_type,
			"score": score,
			"status": verdict_label,
			"feedback": feedback,
			"system_prompt": dynamic_prompt
		})

		print(f"✅ [AI COPILOT JOB COMPLETED] Deliverable: {docname} | Score: {score}% | Verdict: {verdict_label}\n", flush=True)

		publish_stream_event(
			docname, assigned_user,
			f"AI Score: {score}% (threshold: {passing_score}%). Review complete — score is informational.",
			progress=100
		)

		doc.flags.ignore_permissions = True
		doc.flags.ignore_workflow = True
		doc.flags.ignore_validate = True
		doc.save(ignore_permissions=True)

		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"AI Copilot Review failed for Content Item {docname}: {str(e)}")
		frappe.db.set_value("Content Item", docname, "ai_review_status", "Failed", update_modified=False)
		publish_stream_event(docname, None, f"AI Copilot Evaluation failed: {str(e)}", progress=0)
	finally:
		frappe.flags.in_ai_copilot_review = False
