# Copyright (c) 2026, Optimum Data Analytics and Contributors
# See license.txt

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests.utils import FrappeTestCase
from oda_marketing.setup_fixtures import run_setup


class TestContentCalendar(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		run_setup()

	def test_calendar_creation_and_item_linkage(self):
		cal_name = "2026 Q4 Operations Calendar"
		if frappe.db.exists("Content Calendar", cal_name):
			frappe.delete_doc("Content Calendar", cal_name, force=True)

		calendar = frappe.get_doc({
			"doctype": "Content Calendar",
			"calendar_name": cal_name,
			"from_date": "2026-10-01",
			"to_date": "2026-12-31",
			"status": "Active",
			"description": "Testing content calendar creation"
		})
		calendar.insert()
		self.assertEqual(calendar.calendar_name, cal_name)
		self.assertEqual(calendar.status, "Active")

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Q4 Strategy Blog",
			"content_type": "Blog",
			"topic": "Q4 Cloud Strategy Briefing",
			"practice_area": "Cross-domain",
			"content_calendar": calendar.name,
			"planned_publish_date": "2026-10-15",
			"assigned_to": "writer.test@oda.local",
			"reviewer_technical": "Avishkar.Kabadi@optimumdataanalytics.com"
		})
		item.insert()
		self.assertEqual(item.content_calendar, calendar.name)
		self.assertEqual(item.workflow_state, "Planned")

	def test_content_item_workflow_transitions(self):
		cal_name = "2026 Q4 Operations Calendar"
		if not frappe.db.exists("Content Calendar", cal_name):
			frappe.get_doc({
				"doctype": "Content Calendar",
				"calendar_name": cal_name,
				"from_date": "2026-10-01",
				"to_date": "2026-12-31",
				"status": "Active"
			}).insert()

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Workflow Test Item",
			"content_type": "Blog",
			"topic": "Workflow test topic",
			"practice_area": "Fintech",
			"content_calendar": cal_name,
			"planned_publish_date": "2026-11-01",
			"assigned_to": "writer.test@oda.local",
			"reviewer_technical": "Avishkar.Kabadi@optimumdataanalytics.com",
			"workflow_state": "Planned",
			"status": "Planned"
		})
		item.insert()
		self.assertEqual(item.workflow_state, "Planned")

		# Issue Brief -> Briefed
		frappe.set_user("lead.test@oda.local")
		apply_workflow(item, "Issue Brief")
		item.reload()
		self.assertEqual(item.workflow_state, "Briefed")

		# Accept Brief -> In Progress
		frappe.set_user("writer.test@oda.local")
		apply_workflow(item, "Accept Brief")
		item.reload()
		self.assertEqual(item.workflow_state, "In Progress")

		# Submit for Technical Review
		item.content_file_1 = "/files/sample_draft.txt"
		item.ai_score = 92
		item.ai_review_status = "Completed"
		item.save()
		apply_workflow(item, "Submit for Technical Review")
		item.reload()
		self.assertEqual(item.workflow_state, "In Review - Technical")

		# Approve Technical -> Approved
		frappe.set_user("Avishkar.Kabadi@optimumdataanalytics.com")
		apply_workflow(item, "Approve Technical")
		item.reload()
		self.assertEqual(item.workflow_state, "Approved")
