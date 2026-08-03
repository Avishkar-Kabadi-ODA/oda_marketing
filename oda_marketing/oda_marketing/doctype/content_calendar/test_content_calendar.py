# Copyright (c) 2026, Optimum Data Analytics and Contributors
# See license.txt

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests.utils import FrappeTestCase
from oda_marketing.setup_fixtures import run_setup


class TestContentCalendar(FrappeTestCase):
	def setUp(self):
		run_setup()

	def test_calendar_approval_auto_generates_items(self):
		calendar = frappe.get_doc({
			"doctype": "Content Calendar",
			"title": "Test Sprint 1 Calendar",
			"year": "2026",
			"month": "August",
			"description": "Testing auto generation of content items",
			"slots": [
				{
					"slot_title": "AI in Marketing Trends",
					"content_type": "Blog Post",
					"planned_publish_date": "2026-08-05",
					"channel": "Website",
					"target_audience": "B2B Tech Leaders"
				},
				{
					"slot_title": "Product Launch Post",
					"content_type": "Social Post",
					"planned_publish_date": "2026-08-10",
					"channel": "LinkedIn",
					"target_audience": "Industry Professionals"
				}
			]
		})
		calendar.insert()
		self.assertEqual(calendar.status, "Draft")
		self.assertEqual(calendar.docstatus, 0)

		# Submit calendar
		calendar.submit()
		self.assertEqual(calendar.status, "Approved")
		self.assertEqual(calendar.docstatus, 1)

		# Reload calendar to check slots
		calendar.reload()
		for slot in calendar.slots:
			self.assertTrue(bool(slot.content_item))
			item = frappe.get_doc("Content Item", slot.content_item)
			self.assertEqual(item.title, slot.slot_title)
			self.assertEqual(item.content_type, slot.content_type)
			self.assertEqual(item.channel, slot.channel)
			self.assertEqual(item.workflow_state, "Planned")
			self.assertEqual(item.content_calendar, calendar.name)

	def test_content_item_workflow_transitions(self):
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Workflow Test Item",
			"content_type": "Newsletter",
			"channel": "Email",
			"workflow_state": "Planned",
			"status": "Planned"
		})
		item.insert()
		self.assertEqual(item.workflow_state, "Planned")

		# Apply workflow transition Planned -> Briefing
		apply_workflow(item, "Start Briefing")
		self.assertEqual(item.workflow_state, "Briefing")

		# Apply workflow transition Briefing -> Drafting
		apply_workflow(item, "Submit Brief")
		self.assertEqual(item.workflow_state, "Drafting")

		# Apply workflow transition Drafting -> In Review
		apply_workflow(item, "Submit for Review")
		self.assertEqual(item.workflow_state, "In Review")

		# Apply workflow transition In Review -> Approved
		apply_workflow(item, "Approve Content")
		self.assertEqual(item.workflow_state, "Approved")
