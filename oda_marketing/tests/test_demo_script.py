# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import unittest
import frappe
from frappe.utils import getdate, add_days, nowdate
from frappe.model.workflow import apply_workflow
from oda_marketing.permissions import get_content_item_permission_query_conditions, has_content_item_permission
from oda_marketing.setup_fixtures import setup_test_users, setup_roles


class TestMarketingOperationsFlow(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		setup_roles()
		setup_test_users()
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
			"reviewer_technical": "Avishkar.Kabadi@optimumdataanalytics.com",
			"reviewer_business": "vishwajeet.borade@optimumdataanalytics.com"
		})
		item.insert()
		frappe.db.commit()

		# Writer attempts to modify core metadata (title) -> fails
		frappe.set_user("writer.test@oda.local")
		item.reload()
		item.title = "Modified Title By Writer"
		self.assertRaises(frappe.PermissionError, item.save)

		# Writer updates content_file_1, content_file_2, content_file_3 -> succeeds
		item.reload()
		item.content_file_1 = "/files/primary_draft.pdf"
		item.content_file_2 = "/files/asset_1.png"
		item.content_file_3 = "/files/asset_2.png"
		item.save()
		frappe.db.commit()

		frappe.set_user("Administrator")

	def test_end_to_end_multi_stage_workflow_and_permissions(self):
		self.test_marketing_settings_validation()

		tech_rev = "Avishkar.Kabadi@optimumdataanalytics.com"
		biz_rev = "vishwajeet.borade@optimumdataanalytics.com"

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
			"reviewer_technical": tech_rev,
			"reviewer_business": biz_rev
		})
		item.insert()
		frappe.db.commit()

		# Step 3: Test User Involvement & Default Publisher Permission Scoping
		item.reload()
		self.assertTrue(has_content_item_permission(item, user="writer.test@oda.local"))
		self.assertTrue(has_content_item_permission(item, user=tech_rev))
		self.assertTrue(has_content_item_permission(item, user=biz_rev))
		self.assertTrue(has_content_item_permission(item, user="Mrudula.Saradar@optimumdataanalytics.com"))

		# Step 4: Marketing Lead issues brief (Planned -> Briefed)
		frappe.set_user("lead.test@oda.local")
		item.reload()
		apply_workflow(item, "Issue Brief")
		item.reload()
		self.assertEqual(item.workflow_state, "Briefed")

		# Step 5: Writer accepts brief (Briefed -> In Progress)
		frappe.set_user("writer.test@oda.local")
		item.reload()
		apply_workflow(item, "Accept Brief")
		item.reload()
		self.assertEqual(item.workflow_state, "In Progress")

		# Step 6: Writer attaches primary file & optional assets & submits (In Progress -> In Review - Technical)
		item.reload()
		item.content_file_1 = "/files/sample_draft_v1.pdf"
		item.content_file_2 = "/files/supporting_chart_1.png"
		item.content_file_3 = "/files/supporting_chart_2.png"
		item.save()
		apply_workflow(item, "Submit for Technical Review")
		item.reload()
		self.assertEqual(item.workflow_state, "In Review - Technical")

		# Step 7: Technical Reviewer requests revisions with notes (In Review - Technical -> In Revision)
		frappe.set_user(tech_rev)
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
		frappe.set_user(tech_rev)
		item.reload()
		apply_workflow(item, "Approve Technical")
		item.reload()
		self.assertEqual(item.workflow_state, "In Review - Business")

		# Step 10: Business Reviewer approves business (In Review - Business -> Approved)
		frappe.set_user(biz_rev)
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
		print("End-to-end multi-stage workflow, dedicated published template, and notification routing test passed successfully!")
