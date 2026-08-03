# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MarketingSettings(Document):
	def validate(self):
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

