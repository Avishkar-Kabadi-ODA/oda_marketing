# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from oda_marketing.oda_marketing.ai_engine.prompt_subagent import generate_dynamic_system_prompt
from oda_marketing.oda_marketing.ai_engine.evaluator_agent import evaluate_content_item, publish_stream_event


def run_ai_review(docname):
	"""
	Background job orchestrator (frappe.enqueue):
	1. Invokes Subagent to generate dynamic system prompt.
	2. Invokes Primary Evaluator Agent to score the deliverable.
	3. Updates Content Item fields and executes 90% gatekeeper status transition.
	"""
	if not frappe.db.exists("Content Item", docname):
		return

	frappe.flags.in_ai_copilot_review = True

	try:
		doc = frappe.get_doc("Content Item", docname)

		# Mark status as In Progress
		doc.db_set("ai_review_status", "In Progress", update_modified=False)

		assigned_user = doc.assigned_to or doc.owner
		publish_stream_event(docname, assigned_user, "Stage 1: Triggering Prompt Generator Subagent...", progress=10)

		# Stage 1: Generate dynamic system prompt via Subagent
		dynamic_prompt = generate_dynamic_system_prompt(doc)
		doc.db_set("ai_generated_prompt", dynamic_prompt, update_modified=False)

		publish_stream_event(docname, assigned_user, "Stage 2: Evaluating content with dynamic system prompt...", progress=30)

		# Stage 2: Evaluate document via Primary Agent
		eval_res = evaluate_content_item(doc, dynamic_prompt, user_email=assigned_user)

		score = int(eval_res.get("overall_score", 0))
		feedback = eval_res.get("ai_copilot_feedback", "")

		settings = frappe.get_single("Marketing Settings")
		passing_score = int(getattr(settings, "ai_copilot_passing_score", 80) or 80)

		# Update AI fields on Content Item
		doc.ai_score = score
		doc.ai_review_status = "Completed"
		doc.ai_generated_prompt = dynamic_prompt
		doc.ai_copilot_feedback = feedback

		# Stage 3: Gatekeeper Decision Branching (Configurable Threshold)
		if score < passing_score:
			publish_stream_event(
				docname, assigned_user,
				f"AI Score ({score}%) below passing threshold ({passing_score}%). Reverting to 'In Revision'.",
				progress=100
			)

			doc.workflow_state = "In Revision"
			doc.status = "In Revision"
			doc.save(ignore_permissions=True)

			# Notify Content Writer
			notify_writer_copilot_failed(doc, score, feedback)

		else:
			publish_stream_event(
				docname, assigned_user,
				f"AI Score ({score}%) passed threshold ({passing_score}%)! Advancing to Technical Review.",
				progress=100
			)

			doc.workflow_state = "In Review - Technical"
			doc.status = "In Review - Technical"
			doc.save(ignore_permissions=True)

			# Trigger workflow email notification to Technical Reviewer & stakeholders
			try:
				doc.trigger_workflow_notifications()
			except Exception as ne:
				frappe.log_error(f"Error sending Technical Reviewer email for {docname}: {str(ne)}")

		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"AI Copilot Review failed for Content Item {docname}: {str(e)}")
		frappe.db.set_value("Content Item", docname, "ai_review_status", "Failed", update_modified=False)
		publish_stream_event(docname, None, f"AI Copilot Evaluation failed: {str(e)}", progress=0)
	finally:
		frappe.flags.in_ai_copilot_review = False


def notify_writer_copilot_failed(doc, score, feedback):
	"""Sends an automated alert to Content Writer when AI Copilot score is below 90%."""
	if not doc.assigned_to:
		return

	try:
		subject = f"[COPILOT REVISION REQUIRED] Deliverable '{doc.title}' AI Quality Score: {score}%"
		message = f"""<p>Hello <b>{doc.get_user_full_name(doc.assigned_to)}</b>,</p>
<p>Your content deliverable <b>{doc.title}</b> has been evaluated by the <b>Marketing Copilot Agent</b>.</p>
<p><b>AI Quality Score:</b> <span style="color: #dc2626; font-weight: bold;">{score}%</span> (Minimum Required: <b>90%</b>)</p>
<p>The deliverable has been moved to <b>In Revision</b> status. Please review the AI Copilot Feedback below, update your content draft, and resubmit.</p>
<div style="background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 15px; margin: 15px 0;">
  {feedback}
</div>
<p>Log into the portal to review full details and re-upload your draft.</p>
"""
		frappe.sendmail(
			recipients=[doc.assigned_to],
			subject=subject,
			message=message,
			now=False
		)
	except Exception as e:
		frappe.log_error(f"Failed to send Copilot failure notification email for {doc.name}: {str(e)}")
