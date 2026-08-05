# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import unittest
import frappe
from frappe.utils import getdate, add_days, nowdate
from frappe.model.workflow import apply_workflow
from oda_marketing.permissions import get_content_item_permission_query_conditions, has_content_item_permission
from oda_marketing.setup_fixtures import setup_test_users, setup_roles, run_setup


class TestMarketingOperationsFlow(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		run_setup()
		frappe.db.delete("Content Item")
		frappe.db.delete("Content Calendar")
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
			"reviewer_technical": "Avishkar.Kabadi@optimumdataanalytics.com"
		})
		item.insert()
		frappe.db.commit()

		# Writer attempts to modify core metadata (title) -> fails
		frappe.set_user("writer.test@oda.local")
		item.reload()
		item.title = "Modified Title By Writer"
		self.assertRaises(frappe.PermissionError, item.save)

		# Writer attempts to modify SLA due date -> fails
		item.reload()
		item.sla_due_date = "2026-10-10"
		self.assertRaises(frappe.PermissionError, item.save)

		# Writer updates content_file_1, content_file_2, content_file_3 -> succeeds
		item.reload()
		item.content_file_1 = "/files/primary_draft.pdf"
		item.content_file_2 = "/files/asset_1.png"
		item.content_file_3 = "/files/asset_2.png"
		item.save()
		frappe.db.commit()

		frappe.set_user("Administrator")

	def test_sla_lead_time_calculation_and_validations(self):
		frappe.set_user("lead.test@oda.local")
		cal = frappe.get_doc({
			"doctype": "Content Calendar",
			"calendar_name": "SLA Test Calendar",
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"status": "Active"
		}).insert()

		# Set custom SLA lead days to 20 days in settings via db_set and clear cache
		frappe.db.set_single_value("Marketing Settings", "default_sla_lead_days", 20)
		frappe.clear_cache()

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "SLA Lead Time Item",
			"content_type": "Blog",
			"topic": "SLA test",
			"content_calendar": cal.name,
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local",
			"reviewer_technical": "Avishkar.Kabadi@optimumdataanalytics.com"
		})
		item.insert()

		# Verify SLA Due Date is planned_publish_date (2026-09-01) minus 20 days = 2026-08-12
		self.assertEqual(str(item.sla_due_date), "2026-08-12")

		# Test mandatory Published URL validation
		item.workflow_state = "Published"
		item.published_url = ""
		self.assertRaises(frappe.ValidationError, item.save)

		# Test mandatory Technical Reviewer validation
		item.workflow_state = "In Review - Technical"
		item.reviewer_technical = ""
		self.assertRaises(frappe.ValidationError, item.save)

		frappe.set_user("Administrator")

	def test_end_to_end_multi_stage_workflow_and_permissions(self):
		tech_rev = "Avishkar.Kabadi@optimumdataanalytics.com"

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

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "GenAI in Oncology",
			"content_type": "Blog",
			"topic": "Clinical AI decision support",
			"practice_area": "HCLS",
			"content_calendar": cal.name,
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local",
			"reviewer_technical": tech_rev
		})
		item.insert()
		frappe.db.commit()

		item.reload()
		self.assertTrue(has_content_item_permission(item, user="writer.test@oda.local"))
		self.assertTrue(has_content_item_permission(item, user=tech_rev))
		self.assertTrue(has_content_item_permission(item, user="Mrudula.Saradar@optimumdataanalytics.com"))

		# Issue Brief
		frappe.set_user("lead.test@oda.local")
		item.reload()
		apply_workflow(item, "Issue Brief")
		item.reload()
		self.assertEqual(item.workflow_state, "Briefed")

		# Accept Brief
		frappe.set_user("writer.test@oda.local")
		item.reload()
		apply_workflow(item, "Accept Brief")
		item.reload()
		self.assertEqual(item.workflow_state, "In Progress")

		# Submit for Technical Review (Direct flow when AI Copilot is disabled)
		item.reload()
		item.content_file_1 = "/files/sample_draft.txt"
		item.save()
		apply_workflow(item, "Submit for Technical Review")
		item.reload()
		self.assertEqual(item.workflow_state, "In Review - Technical")

		# Request Changes
		frappe.set_user(tech_rev)
		item.reload()
		item.revision_feedback_notes = "Please clarify the FDA compliance section on page 3."
		item.save()
		apply_workflow(item, "Request Changes")
		item.reload()
		self.assertEqual(item.workflow_state, "In Revision")

		# Resubmit Draft
		frappe.set_user("writer.test@oda.local")
		item.reload()
		item.content_file_1 = "/files/sample_draft.txt"
		item.save()
		apply_workflow(item, "Submit for Technical Review")
		item.reload()
		self.assertEqual(item.workflow_state, "In Review - Technical")

		# Approve Technical -> Approved
		frappe.set_user(tech_rev)
		item.reload()
		apply_workflow(item, "Approve Technical")
		item.reload()
		self.assertEqual(item.workflow_state, "Approved")

		# Publish -> Published
		frappe.set_user("lead.test@oda.local")
		item.reload()
		item.published_url = "https://optimumdataanalytics.com/blogs/genai-oncology"
		item.save()
		apply_workflow(item, "Publish")
		item.reload()
		self.assertEqual(item.workflow_state, "Published")

		frappe.set_user("Administrator")
		print("End-to-end multi-stage workflow, email CTA button links, and targeted notification test passed successfully!")

	def test_ai_copilot_resubmission_from_revision(self):
		frappe.db.set_single_value("Marketing Settings", "enable_ai_copilot", 1)
		frappe.db.set_single_value("Marketing Settings", "ai_copilot_passing_score", 80)
		frappe.clear_cache()

		tech_rev = "Avishkar.Kabadi@optimumdataanalytics.com"
		frappe.set_user("lead.test@oda.local")

		cal = frappe.get_doc({
			"doctype": "Content Calendar",
			"calendar_name": "Copilot Test Cal 2026",
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"status": "Active"
		}).insert()

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "AI Copilot Resubmit Item",
			"content_type": "Blog",
			"topic": "Testing AI re-evaluation from In Revision",
			"practice_area": "HCLS",
			"content_calendar": cal.name,
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local",
			"reviewer_technical": tech_rev,
			"content_file_1": "/files/sample_draft.txt"
		}).insert()

		# Technical Reviewer requests changes -> In Revision
		item.db_set({
			"ai_score": 90,
			"ai_review_status": "Completed",
			"workflow_state": "In Review - Technical"
		}, update_modified=False)
		item.reload()
		item.revision_feedback_notes = "Please update draft section 2."
		item.save()

		frappe.set_user(tech_rev)
		apply_workflow(item, "Request Changes")
		item.reload()
		self.assertEqual(item.workflow_state, "In Revision")

		# Writer resubmits draft -> enters Marketing Copilot Review, triggers AI evaluation, and moves to evaluated state
		frappe.set_user("writer.test@oda.local")
		item.reload()
		item.content_file_1 = "/files/updated_draft.txt"
		item.save()
		apply_workflow(item, "Resubmit Draft")
		item.reload()
		self.assertEqual(item.ai_review_status, "Completed")
		self.assertIn(item.workflow_state, ["In Revision", "In Review - Technical"])

		frappe.set_user("Administrator")
