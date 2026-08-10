# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MarketingSettings(Document):
	def validate(self):
		if getattr(self, "default_sla_lead_days", None) is not None:
			val = int(self.default_sla_lead_days or 0)
			if val < 0:
				frappe.throw(_("<b>Default SLA Lead Time (Days)</b> cannot be negative."))

		if self.enable_email_notifications:
			mandatory_fields = [
				"default_publisher",
				"writer_email_template",
				"reviewer_email_template",
				"publisher_email_template",
				"published_email_template",
				"overdue_sla_email_template"
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

			max_writer_reviews = int(getattr(self, "max_writer_copilot_reviews_per_item", 3) or 3)
			if max_writer_reviews < 1:
				frappe.throw(_("<b>Max Writer Copilot Reviews per Item</b> must be at least 1."))

			max_reviewer_reviews = int(getattr(self, "max_reviewer_copilot_reviews_per_item", 3) or 3)
			if max_reviewer_reviews < 1:
				frappe.throw(_("<b>Max Reviewer Copilot Reviews per Item</b> must be at least 1."))

		if getattr(self, "sla_reminder_enabled", 0):
			days_before = int(getattr(self, "sla_reminder_days_before", 0) or 0)
			if days_before < 1:
				frappe.throw(_("<b>Reminder Days Before Due Date</b> must be at least 1 when reminders are enabled."))
