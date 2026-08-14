# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MarketingSettings(Document):
	def validate(self):
		if getattr(self, "business_hours_start", None) is None:
			self.business_hours_start = 9
		if getattr(self, "business_hours_end", None) is None:
			self.business_hours_end = 19

		start_h = int(self.business_hours_start) if self.business_hours_start is not None else 9
		end_h = int(self.business_hours_end) if self.business_hours_end is not None else 19

		if not (0 <= start_h <= 23):
			frappe.throw(_("<b>Business Hours Start</b> must be between 0 and 23."))
		if not (0 <= end_h <= 23):
			frappe.throw(_("<b>Business Hours End</b> must be between 0 and 23."))
		if start_h >= end_h:
			frappe.throw(_("<b>Business Hours Start</b> must be earlier than <b>Business Hours End</b>."))

		if self.enable_email_notifications:
			mandatory_fields = [
				"default_publisher",
				"writer_email_template",
				"reviewer_email_template",
				"publisher_email_template",
				"published_email_template",
				"overdue_email_template"
			]
			for field in mandatory_fields:
				if not getattr(self, field, None):
					frappe.throw(_("Field <b>{0}</b> is mandatory when Email Notifications are enabled.").format(self.meta.get_label(field)))

		if self.enable_ai_copilot:
			ai_mandatory_fields = [
				"ai_copilot_passing_score",
				"ai_provider",
				"ai_api_key_var",
				"ai_endpoint_var",
				"ai_model_name",
				"subagent_meta_prompt",
				"evaluator_default_prompt"
			]
			for field in ai_mandatory_fields:
				if not getattr(self, field, None):
					frappe.throw(_("Field <b>{0}</b> is mandatory when AI Copilot is enabled.").format(self.meta.get_label(field)))

			max_writer_reviews = int(getattr(self, "max_writer_copilot_reviews_per_item", 2) or 2)
			if max_writer_reviews < 1:
				frappe.throw(_("<b>Max Writer Copilot Reviews per Item</b> must be at least 1."))

			max_reviewer_reviews = int(getattr(self, "max_reviewer_copilot_reviews_per_item", 2) or 2)
			if max_reviewer_reviews < 1:
				frappe.throw(_("<b>Max Reviewer Copilot Reviews per Item</b> must be at least 1."))

		if getattr(self, "sla_reminder_enabled", 0):
			days_before = int(getattr(self, "sla_reminder_days_before", 0) or 0)
			if days_before < 1:
				frappe.throw(_("<b>Reminder Days Before Due Date</b> must be at least 1 when reminders are enabled."))


@frappe.whitelist()
def get_publisher_users(doctype, txt, searchfield, start, page_len, filters):
	"""Filters Default Publisher dropdown in Marketing Settings to show enabled System Users holding Marketing Lead or System Manager role, or Administrator."""
	return frappe.db.sql("""
		SELECT DISTINCT u.name, CONCAT_WS(' ', u.first_name, u.last_name)
		FROM `tabUser` u
		LEFT JOIN `tabHas Role` r ON r.parent = u.name
		WHERE u.enabled = 1 AND u.user_type = 'System User'
		AND (r.role IN ('Marketing Lead', 'System Manager') OR u.name = 'Administrator')
		AND (u.name LIKE %s OR u.first_name LIKE %s OR u.last_name LIKE %s)
		ORDER BY u.name ASC
		LIMIT %s, %s
	""", (f"%{txt}%", f"%{txt}%", f"%{txt}%", int(start or 0), int(page_len or 20)))
