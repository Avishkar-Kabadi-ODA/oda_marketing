# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import unittest
import frappe
from frappe.utils import getdate, add_days, nowdate
from frappe.model.workflow import apply_workflow
from oda_marketing.permissions import get_content_item_permission_query_conditions, has_content_item_permission


class TestMarketingOperationsFlow(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		# Clear existing records
		frappe.db.delete("Content Brief")
		frappe.db.delete("Content Item")
		frappe.db.delete("Content Calendar")
		frappe.db.commit()

	def test_marketing_settings_validation(self):
		settings = frappe.get_single("Marketing Settings")
		settings.reload()
		settings.enable_email_notifications = 1
		settings.default_publisher = "lead.test@oda.local"
		settings.writer_email_template = "Marketing Writer Notification"
		settings.reviewer_email_template = "Marketing Reviewer Notification"
		settings.publisher_email_template = "Marketing Publisher Notification"
		settings.overdue_sla_email_template = "Marketing Overdue SLA Alert"
		settings.save()
		frappe.db.commit()

	def test_strict_role_creation_and_editing_permissions(self):
		frappe.set_user("lead.test@oda.local")
		cal = frappe.get_doc({
			"doctype": "Content Calendar",
			"calendar_name": "2026 Operations Calendar",
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"status": "Active"
		}).insert()

		# Test Writer CANNOT create a new Content Item
		frappe.set_user("writer.test@oda.local")
		item_unauthorized = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Unauthorized Item",
			"content_type": "Blog",
			"topic": "Unauthorized creation",
			"content_calendar": cal.name,
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local"
		})
		self.assertRaises(frappe.PermissionError, item_unauthorized.insert)

		# Lead creates the item successfully
		frappe.set_user("lead.test@oda.local")
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Authorized Item",
			"content_type": "Blog",
			"topic": "Authorized creation",
			"content_calendar": cal.name,
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local",
			"reviewer_technical": "techrev.test@oda.local",
			"reviewer_business": "bizrev.test@oda.local"
		})
		item.insert()
		frappe.db.commit()

		# Writer attempts to modify core metadata (title) -> fails
		frappe.set_user("writer.test@oda.local")
		item.reload()
		item.title = "Modified Title By Writer"
		self.assertRaises(frappe.PermissionError, item.save)

		# Writer updates content_file_1 -> succeeds
		item.reload()
		item.content_file_1 = "/files/valid_writer_attachment.pdf"
		item.save()
		frappe.db.commit()

		frappe.set_user("Administrator")

	def test_end_to_end_multi_stage_workflow_and_permissions(self):
		self.test_marketing_settings_validation()

		# Step 1: Create Master Setup Calendar
		frappe.set_user("lead.test@oda.local")

		cal = frappe.get_doc({
			"doctype": "Content Calendar",
			"calendar_name": "2026 Operations Calendar",
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"status": "Active",
			"description": "Master 2026 Content Calendar setup"
		})
		cal.insert()
		frappe.db.commit()

		# Step 2: Create Content Item (State: Planned)
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "GenAI in Oncology",
			"content_type": "Blog",
			"topic": "Clinical AI decision support",
			"practice_area": "HCLS",
			"content_calendar": cal.name,
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local",
			"reviewer_technical": "techrev.test@oda.local",
			"reviewer_business": "bizrev.test@oda.local"
		})
		item.insert()
		frappe.db.commit()

		# Test Brief Mandatory Validation when moving to Briefed
		frappe.set_user("lead.test@oda.local")
		self.assertRaises(frappe.ValidationError, apply_workflow, item, "Issue Brief")

		# Create linked Content Brief
		brief = frappe.get_doc({
			"doctype": "Content Brief",
			"content_item": item.name,
			"outline": "Cover clinical validation and ROI",
			"target_audience": "Hospital Directors",
			"primary_keyword": "oncology ai",
			"word_target": 1500,
			"accepted_by_writer": 0
		})
		brief.insert()
		item.reload()
		item.content_brief = brief.name
		item.save()
		frappe.db.commit()

		# Step 3: Test User Involvement & Default Publisher Permission Scoping
		self.assertTrue(has_content_item_permission(item, user="writer.test@oda.local"))
		self.assertTrue(has_content_item_permission(item, user="techrev.test@oda.local"))
		self.assertTrue(has_content_item_permission(item, user="bizrev.test@oda.local"))
		self.assertTrue(has_content_item_permission(item, user="lead.test@oda.local"))

		# Step 4: Marketing Lead issues brief (Planned -> Briefed)
		frappe.set_user("lead.test@oda.local")
		item.reload()
		apply_workflow(item, "Issue Brief")
		item.reload()
		self.assertEqual(item.workflow_state, "Briefed")

		# Step 5: Writer accepts brief (Briefed -> In Progress)
		frappe.set_user("writer.test@oda.local")
		brief.reload()
		brief.accepted_by_writer = 1
		brief.save()
		item.reload()
		self.assertEqual(item.workflow_state, "In Progress")

		# Test Primary Attachment Mandatory Validation when submitting for review
		item.reload()
		item.content_file_1 = ""
		self.assertRaises(frappe.ValidationError, apply_workflow, item, "Submit for Technical Review")

		# Step 6: Writer attaches primary file & submits (In Progress -> In Review - Technical)
		item.reload()
		item.content_file_1 = "/files/sample_draft_v1.pdf"
		item.content_file_2 = "/files/supporting_chart.png"
		item.save()
		apply_workflow(item, "Submit for Technical Review")
		item.reload()
		self.assertEqual(item.workflow_state, "In Review - Technical")

		# Step 7: Technical Reviewer requests revisions with notes (In Review - Technical -> In Revision)
		frappe.set_user("techrev.test@oda.local")
		item.reload()
		item.revision_feedback_notes = "Please clarify the FDA compliance section on page 3."
		item.save()
		apply_workflow(item, "Request Changes")
		item.reload()
		self.assertEqual(item.workflow_state, "In Revision")

		# Step 8: Writer resubmits draft (In Revision -> In Review - Technical)
		frappe.set_user("writer.test@oda.local")
		item.reload()
		item.content_file_1 = "/files/sample_draft_v2.pdf"
		item.save()
		apply_workflow(item, "Resubmit Draft")
		item.reload()
		self.assertEqual(item.workflow_state, "In Review - Technical")

		# Step 9: Technical Reviewer approves technical (In Review - Technical -> In Review - Business)
		frappe.set_user("techrev.test@oda.local")
		item.reload()
		apply_workflow(item, "Approve Technical")
		item.reload()
		self.assertEqual(item.workflow_state, "In Review - Business")

		# Step 10: Business Reviewer approves business (In Review - Business -> Approved)
		frappe.set_user("bizrev.test@oda.local")
		item.reload()
		apply_workflow(item, "Approve Business")
		item.reload()
		self.assertEqual(item.workflow_state, "Approved")

		# Step 11: Default Publisher / Lead publishes asset (Approved -> Published)
		frappe.set_user("lead.test@oda.local")
		item.reload()
		item.published_url = "https://optimumdataanalytics.com/blogs/genai-oncology"
		item.save()
		apply_workflow(item, "Publish")
		item.reload()
		self.assertEqual(item.workflow_state, "Published")

		frappe.set_user("Administrator")
		print("End-to-end multi-stage workflow, strict role permissions, and attachment access test passed successfully!")
