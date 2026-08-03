# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class ContentBrief(Document):
	def validate(self):
		if self.accepted_by_writer and not self.accepted_on:
			self.accepted_on = now_datetime()

		if self.content_item:
			existing = frappe.db.get_value("Content Brief", {"content_item": self.content_item, "name": ["!=", self.name]}, "name")
			if existing:
				frappe.throw(_("Content Item '{0}' already has a linked Content Brief ({1}). Only 1 Content Brief is allowed per Content Item.").format(self.content_item, existing))

	def on_update(self):
		if self.content_item:
			frappe.db.set_value("Content Item", self.content_item, "content_brief", self.name)

			if self.accepted_by_writer:
				item = frappe.get_doc("Content Item", self.content_item)
				if item.workflow_state in ["Briefed", "Planned"]:
					item.db_set("workflow_state", "In Progress")
					frappe.msgprint(_("Content Brief accepted. Content Item '{0}' is now 'In Progress'.").format(item.title), alert=True)
