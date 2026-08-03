# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ContentBrief(Document):
	def validate(self):
		if self.accepted_by_writer and not self.accepted_on:
			self.accepted_on = now_datetime()

	def on_update(self):
		if self.accepted_by_writer and self.content_item:
			item = frappe.get_doc("Content Item", self.content_item)
			if item.workflow_state in ["Briefed", "Planned"]:
				item.db_set("workflow_state", "In Progress")
				frappe.msgprint(f"Content Brief accepted. Content Item '{item.title}' is now 'In Progress'.", alert=True)
