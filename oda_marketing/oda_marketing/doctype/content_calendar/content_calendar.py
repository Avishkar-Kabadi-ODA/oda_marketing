# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ContentCalendar(Document):
	def on_submit(self):
		self.db_set("status", "Approved")
		self.generate_content_items()

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def generate_content_items(self):
		if not self.slots:
			frappe.throw("Cannot approve a Content Calendar with no slots.")

		created_count = 0
		for slot in self.slots:
			if slot.content_item:
				continue  # Skip if already generated

			# 1. Create Content Brief
			brief = frappe.get_doc({
				"doctype": "Content Brief",
				"brief_title": f"Brief: {slot.slot_title}",
				"target_audience": slot.target_audience or "",
				"assigned_owner": slot.assigned_owner,
				"status": "Draft"
			})
			brief.insert(ignore_permissions=True)

			# 2. Create Content Item
			item = frappe.get_doc({
				"doctype": "Content Item",
				"title": slot.slot_title,
				"content_type": slot.content_type,
				"planned_publish_date": slot.planned_publish_date,
				"channel": slot.channel,
				"assigned_owner": slot.assigned_owner,
				"content_calendar": self.name,
				"calendar_slot": slot.name,
				"content_brief": brief.name,
				"workflow_state": "Planned",
				"status": "Planned"
			})
			item.insert(ignore_permissions=True)

			# 3. Link back
			brief.db_set("content_item", item.name)
			slot.db_set("content_item", item.name)
			created_count += 1

		frappe.msgprint(
			f"Successfully approved calendar '{self.title}' and auto-generated {created_count} Content Item(s) & Brief(s).",
			alert=True
		)
