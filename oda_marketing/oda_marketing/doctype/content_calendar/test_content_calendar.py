# Copyright (c) 2026, Optimum Data Analytics and Contributors
# See license.txt

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests.utils import FrappeTestCase
from oda_marketing.tests.test_demo_script import (
	TEST_LEAD,
	TEST_REVIEWER,
	TEST_WRITER,
	create_unit_test_users,
)


class TestContentCalendar(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		create_unit_test_users()
		for option_type, labels in (
			("Format", ("Blog",)),
			("Industry Domain", ("Cross-domain", "Fintech")),
		):
			for label in labels:
				if not frappe.db.exists("Content Item Option", label):
					frappe.get_doc({
						"doctype": "Content Item Option",
						"option_type": option_type,
						"option_label": label,
						"is_active": 1,
					}).insert(ignore_permissions=True)

	def test_calendar_creation_and_item_linkage(self):
		cal_name = f"2026 Q4 Operations Calendar {frappe.generate_hash(length=8)}"

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
			"description": "Q4 Cloud Strategy Briefing",
			"industry_domain": "Cross-domain",
			"content_calendar": calendar.name,
			"planned_publish_date": "2026-10-15",
			"due_date": "2026-10-10",
			"assigned_to": TEST_WRITER,
			"reviewer_technical": TEST_REVIEWER
		})
		item.insert()
		self.assertEqual(item.content_calendar, calendar.name)
		self.assertEqual(item.workflow_state, "Planned")

	def test_content_item_workflow_transitions(self):
		cal_name = f"2026 Q4 Operations Calendar {frappe.generate_hash(length=8)}"
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
			"description": "Workflow test topic",
			"industry_domain": "Fintech",
			"content_calendar": cal_name,
			"planned_publish_date": "2026-11-01",
			"due_date": "2026-10-25",
			"assigned_to": TEST_WRITER,
			"reviewer_technical": TEST_REVIEWER,
			"workflow_state": "Planned",
			"status": "Planned"
		})
		item.insert()
		self.assertEqual(item.workflow_state, "Planned")

		# Issue Brief -> Briefed
		frappe.set_user(TEST_LEAD)
		apply_workflow(item, "Issue Brief")
		item.reload()
		self.assertEqual(item.workflow_state, "Briefed")

		# Start Work -> In Progress (renamed from "Accept Brief")
		frappe.set_user(TEST_WRITER)
		apply_workflow(item, "Start Work")
		item.reload()
		self.assertEqual(item.workflow_state, "In Progress")

		# Submit for Review (renamed from "Submit for Technical Review")
		item.content_file_1 = "/files/sample_draft.md"
		item.save()
		apply_workflow(item, "Submit for Review")
		item.reload()
		self.assertEqual(item.workflow_state, "In Review")

		# Approve -> Approved (renamed from "Approve Technical")
		frappe.set_user(TEST_REVIEWER)
		apply_workflow(item, "Approve")
		item.reload()
		self.assertEqual(item.workflow_state, "Approved")
