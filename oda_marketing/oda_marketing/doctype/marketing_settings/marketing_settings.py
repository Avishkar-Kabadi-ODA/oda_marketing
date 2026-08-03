# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MarketingSettings(Document):
	def validate(self):
		if self.enable_email_notifications:
			mandatory_templates = [
				("writer_email_template", "Writer Email Template"),
				("reviewer_email_template", "Reviewer Email Template"),
				("publisher_email_template", "Publisher Email Template"),
				("overdue_sla_email_template", "Overdue SLA Escalation Template")
			]
			for field, label in mandatory_templates:
				if not getattr(self, field, None):
					frappe.throw(_("<b>{0}</b> is mandatory when Email Notifications are enabled.").format(label))
