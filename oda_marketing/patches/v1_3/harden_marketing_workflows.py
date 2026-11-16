# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.db.set_value(
		"Content Item Option",
		{"option_type": "Practice Area"},
		"option_type",
		"Industry Domain",
		update_modified=False,
	)

	frappe.db.sql(
		"""
		UPDATE `tabContent Item`
		SET ai_review_started_on = modified
		WHERE ai_review_status IN ('Queued', 'In Progress')
		AND ai_review_started_on IS NULL
		"""
	)

	workflow_name = "Content Item Workflow"
	if frappe.db.exists("Workflow", workflow_name):
		workflow = frappe.get_doc("Workflow", workflow_name)
		publish_transitions = [
			transition
			for transition in workflow.transitions
			if transition.state == "Approved"
			and transition.action == "Publish"
			and transition.next_state == "Published"
		]
		if publish_transitions and not any(
			transition.allowed == "Desk User" for transition in publish_transitions
		):
			workflow.append(
				"transitions",
				{
					"state": "Approved",
					"action": "Publish",
					"next_state": "Published",
					"allowed": "Desk User",
				},
			)
			workflow.save(ignore_permissions=True)

	settings = frappe.get_single("Marketing Settings")
	replacements = (
		(
			"Award high passing scores (85%–98%) for complete, well-written enterprise deliverables.",
			"Score each criterion based on evidence in the draft; do not assume or target a particular score.",
		),
		(
			"Award high passing scores (85%–98%) for complete, well-written, publishable enterprise content.",
			"Score each criterion based on evidence in the draft; do not assume or target a particular score.",
		),
		("Passing threshold is 80%.", "Passing threshold is {passing_score}%. The score is informational."),
	)
	for fieldname in ("subagent_meta_prompt", "evaluator_default_prompt"):
		value = getattr(settings, fieldname, None)
		if not value:
			continue
		updated = value
		for old_text, new_text in replacements:
			updated = updated.replace(old_text, new_text)
		if updated != value:
			frappe.db.set_value(
				"Marketing Settings",
				"Marketing Settings",
				fieldname,
				updated,
				update_modified=False,
			)
