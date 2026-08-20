# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from oda_marketing.oda_marketing.doctype.content_item.content_item import (
	get_reviewer_users,
	get_assigned_to_users,
	get_dashboard_metrics,
	import_content_items_from_excel
)
from oda_marketing.permissions import (
	get_content_item_permission_query_conditions,
	has_content_item_permission
)
import openpyxl
import io
import os


class TestPermissionsAndFeatures(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		# Create test calendar if not exists
		if not frappe.db.exists("Content Calendar", "2026 Test Calendar"):
			cal = frappe.get_doc({
				"doctype": "Content Calendar",
				"calendar_name": "2026 Test Calendar",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"status": "Active"
			})
			cal.insert(ignore_permissions=True)

		# Ensure options exist
		if not frappe.db.exists("Content Item Option", "Blog"):
			frappe.get_doc({
				"doctype": "Content Item Option",
				"option_type": "Format",
				"option_label": "Blog",
				"is_active": 1
			}).insert(ignore_permissions=True)

		if not frappe.db.exists("Content Item Option", "HCLS"):
			frappe.get_doc({
				"doctype": "Content Item Option",
				"option_type": "Industry Domain",
				"option_label": "HCLS",
				"is_active": 1
			}).insert(ignore_permissions=True)

		# Create test users
		for email, role in [("test_writer_1@example.com", None), ("test_reviewer_1@example.com", None), ("test_lead_1@example.com", "Marketing Lead"), ("test_lead_2@example.com", "Marketing Lead")]:
			if not frappe.db.exists("User", email):
				user_dict = {
					"doctype": "User",
					"email": email,
					"first_name": email.split("@")[0],
					"enabled": 1,
					"user_type": "System User"
				}
				if role:
					user_dict["roles"] = [{"role": role}]
				user = frappe.get_doc(user_dict)
				user.insert(ignore_permissions=True)
			elif role:
				u = frappe.get_doc("User", email)
				u.add_roles(role)

		frappe.flags.mute_emails = True
		settings = frappe.get_single("Marketing Settings")
		settings.enable_email_notifications = 0
		settings.save(ignore_permissions=True)

	def test_mutual_exclusion_validation(self):
		"""Ensures writer and reviewer cannot be the same user."""
		doc = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Mutual Exclusion Test",
			"content_type": "Blog",
			"description": "Test description",
			"content_calendar": "2026 Test Calendar",
			"planned_publish_date": "2026-09-15",
			"due_date": "2026-09-01",
			"assigned_to": "test_writer_1@example.com",
			"reviewer_technical": "test_writer_1@example.com"
		})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_planned_state_privacy(self):
		"""Ensures writers cannot view items in Planned state until briefed."""
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Planned Privacy Test Item",
			"content_type": "Blog",
			"description": "Testing planned state privacy scoping.",
			"content_calendar": "2026 Test Calendar",
			"planned_publish_date": "2026-09-15",
			"due_date": "2026-09-01",
			"assigned_to": "test_writer_1@example.com",
			"reviewer_technical": "test_reviewer_1@example.com",
			"workflow_state": "Planned",
			"status": "Planned"
		})
		item.insert(ignore_permissions=True)

		# Check permission query condition for writer
		cond = get_content_item_permission_query_conditions("test_writer_1@example.com")
		self.assertIn("!= 'Planned'", cond)

		# Check has_content_item_permission for writer on Planned item
		self.assertFalse(has_content_item_permission(item, "read", "test_writer_1@example.com"))

		# Now move item to Briefed
		item.workflow_state = "Briefed"
		item.status = "Briefed"
		item.save(ignore_permissions=True)

		# Now writer should have read access
		self.assertTrue(has_content_item_permission(item, "read", "test_writer_1@example.com"))

	def test_document_level_role_scoping(self):
		"""Ensures a user assigned as author gets treated strictly as Writer, and Lead reviewer retains Lead authority."""
		from frappe.model.workflow import apply_workflow
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Document Level Role Test",
			"content_type": "Blog",
			"description": "Reviewer writing an article.",
			"content_calendar": "2026 Test Calendar",
			"planned_publish_date": "2026-09-15",
			"due_date": "2026-09-01",
			"assigned_to": "test_reviewer_1@example.com",
			"reviewer_technical": "test_lead_1@example.com",
			"workflow_state": "Planned",
			"status": "Planned"
		})
		item.insert(ignore_permissions=True)
		apply_workflow(item, "Issue Brief")

		effective_role = item.get_user_effective_role("test_reviewer_1@example.com")
		self.assertEqual(effective_role, "Writer")

		lead_reviewer_role = item.get_user_effective_role("test_lead_1@example.com")
		self.assertEqual(lead_reviewer_role, "Lead")

	def test_dropdown_filters_and_exclusion(self):
		"""Tests dropdown whitelist methods and mutual exclusion filters."""
		assigned_users = get_assigned_to_users(filters={"reviewer_technical": "test_reviewer_1@example.com"})
		assigned_names = [u[0] for u in assigned_users]
		self.assertNotIn("test_reviewer_1@example.com", assigned_names)

		reviewer_users = get_reviewer_users(filters={"assigned_to": "test_reviewer_1@example.com"})
		reviewer_names = [u[0] for u in reviewer_users]
		self.assertNotIn("test_reviewer_1@example.com", reviewer_names)

	def test_excel_import_defaulting_to_planned(self):
		"""Tests Excel importer batch creation with Planned status default."""
		wb = openpyxl.Workbook()
		ws = wb.active
		ws.append(["Title", "Format", "Description", "Industry Domain", "Content Calendar", "Planned Publish Date", "Due Date", "Assigned To", "Reviewer", "Notes"])
		ws.append([
			"Excel Import Test Blog 1",
			"Blog",
			"Enterprise cloud management test topic description.",
			"HCLS",
			"2026 Test Calendar",
			"2026-10-15",
			"2026-10-01",
			"test_writer_1@example.com",
			"test_reviewer_1@example.com",
			"Test note"
		])
		ws.append([
			"Excel Import Test Blog 2",
			"Blog",
			"Data analytics best practices topic description.",
			"HCLS",
			"2026 Test Calendar",
			"2026-10-20",
			"2026-10-05",
			"test_writer_1@example.com",
			"test_reviewer_1@example.com",
			"Test note 2"
		])

		test_file_path = frappe.get_site_path("public", "files", "test_content_import.xlsx")
		os.makedirs(os.path.dirname(test_file_path), exist_ok=True)
		wb.save(test_file_path)

		res = import_content_items_from_excel(file_url="/files/test_content_import.xlsx", default_calendar="2026 Test Calendar")
		self.assertTrue(res["success"])
		self.assertEqual(res["created_count"], 2)
		self.assertEqual(res["error_count"], 0)

		# Verify items were created in Planned state
		for created in res["created_items"]:
			doc = frappe.get_doc("Content Item", created["name"])
			self.assertEqual(doc.workflow_state, "Planned")
			self.assertEqual(doc.status, "Planned")

		if os.path.exists(test_file_path):
			os.remove(test_file_path)

	def test_dashboard_metrics_api(self):
		"""Tests dashboard metrics calculation across calendar and periods."""
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Dashboard Metric Test Item",
			"content_type": "Blog",
			"description": "Testing dashboard metrics calculation.",
			"content_calendar": "2026 Test Calendar",
			"planned_publish_date": "2026-09-15",
			"due_date": "2026-09-01",
			"assigned_to": "test_writer_1@example.com",
			"reviewer_technical": "test_reviewer_1@example.com",
			"workflow_state": "Planned",
			"status": "Planned"
		})
		item.insert(ignore_permissions=True)

		metrics = get_dashboard_metrics(calendar="2026 Test Calendar", year="2026", month="0")
		self.assertIn("kpis", metrics)
		self.assertIn("status_distribution", metrics)
		self.assertIn("format_distribution", metrics)
		self.assertIn("monthly_trend", metrics)
		self.assertGreaterEqual(metrics["kpis"]["total"], 1)

	def test_lead_metadata_edit_in_progress(self):
		"""Ensures assigned author Lead is scoped as Writer for that item, while unassigned Lead retains Lead metadata editing rights."""
		from frappe.model.workflow import apply_workflow
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Lead Metadata Edit Test",
			"content_type": "Blog",
			"description": "Testing lead metadata edit in progress.",
			"content_calendar": "2026 Test Calendar",
			"planned_publish_date": "2026-09-15",
			"due_date": "2026-09-01",
			"assigned_to": "test_lead_1@example.com",
			"reviewer_technical": "test_reviewer_1@example.com",
			"workflow_state": "Planned",
			"status": "Planned"
		})
		item.insert(ignore_permissions=True)

		apply_workflow(item, "Issue Brief")
		apply_workflow(item, "Start Work")
		self.assertEqual(item.workflow_state, "In Progress")

		# Assigned author Lead (test_lead_1) acts as Writer for this item, cannot modify core metadata
		frappe.set_user("test_lead_1@example.com")
		item_writer = frappe.get_doc("Content Item", item.name)
		item_writer.title = "Attempted Title Change by Assigned Lead"
		self.assertRaises(frappe.PermissionError, item_writer.save)

		# Unassigned Lead (test_lead_2) retains Lead status for this item, can modify core metadata
		frappe.set_user("test_lead_2@example.com")
		item_lead = frappe.get_doc("Content Item", item.name)
		item_lead.assigned_to = "test_writer_1@example.com"
		item_lead.save()
		self.assertEqual(item_lead.assigned_to, "test_writer_1@example.com")
		frappe.set_user("Administrator")

	def test_writer_workflow_transitions(self):
		"""Ensures Content Writer can execute Start Work (Briefed -> In Progress) and Submit for Review (In Progress -> In Review)."""
		from frappe.model.workflow import apply_workflow

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Writer Transition Test Item",
			"content_type": "Blog",
			"description": "Testing writer workflow transitions.",
			"content_calendar": "2026 Test Calendar",
			"planned_publish_date": "2026-09-15",
			"due_date": "2026-09-01",
			"assigned_to": "test_writer_1@example.com",
			"reviewer_technical": "test_reviewer_1@example.com",
			"workflow_state": "Planned",
			"status": "Planned"
		})
		item.insert(ignore_permissions=True)

		# Move to Briefed
		apply_workflow(item, "Issue Brief")
		self.assertEqual(item.workflow_state, "Briefed")

		# Writer executes: Briefed -> In Progress (Start Work)
		frappe.set_user("test_writer_1@example.com")
		item = frappe.get_doc("Content Item", item.name)
		apply_workflow(item, "Start Work")
		self.assertEqual(item.workflow_state, "In Progress")

		# Attach required primary draft & Writer executes: In Progress -> In Review (Submit for Review)
		item = frappe.get_doc("Content Item", item.name)
		item.content_file_1 = "/files/primary_draft.pdf"
		item.save()
		apply_workflow(item, "Submit for Review")
		self.assertEqual(item.workflow_state, "In Review")
		frappe.set_user("Administrator")

	def test_attachment_readonly_before_inprogress(self):
		"""Ensures Content Writer cannot edit attachments or notes in Briefed state, but can in In Progress state."""
		from frappe.model.workflow import apply_workflow

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Attachment Readonly Test Item",
			"content_type": "Blog",
			"description": "Testing attachment locking before in progress.",
			"content_calendar": "2026 Test Calendar",
			"planned_publish_date": "2026-09-15",
			"due_date": "2026-09-01",
			"assigned_to": "test_writer_1@example.com",
			"reviewer_technical": "test_reviewer_1@example.com",
			"workflow_state": "Planned",
			"status": "Planned"
		})
		item.insert(ignore_permissions=True)
		apply_workflow(item, "Issue Brief")

		frappe.set_user("test_writer_1@example.com")
		item = frappe.get_doc("Content Item", item.name)
		item.notes = "Attempting note edit in Briefed state"
		self.assertRaises(frappe.PermissionError, item.save)

		# Start Work moves to In Progress
		apply_workflow(item, "Start Work")

		# Now in In Progress state, writer can edit notes/attachments
		item = frappe.get_doc("Content Item", item.name)
		item.notes = "Note edit in In Progress state"
		item.save()
		self.assertEqual(item.notes, "Note edit in In Progress state")
		frappe.set_user("Administrator")

	def test_lead_as_reviewer_can_issue_brief_and_edit_metadata(self):
		"""Ensures a Marketing Lead who is assigned as reviewer_technical can Issue Brief and edit metadata."""
		from frappe.model.workflow import apply_workflow

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Lead Reviewer Test Item",
			"content_type": "Blog",
			"description": "Testing Lead who is reviewer issuing brief.",
			"content_calendar": "2026 Test Calendar",
			"planned_publish_date": "2026-09-15",
			"due_date": "2026-09-01",
			"assigned_to": "test_writer_1@example.com",
			"reviewer_technical": "test_lead_1@example.com",
			"workflow_state": "Planned",
			"status": "Planned"
		})
		item.insert(ignore_permissions=True)

		# Lead (who is reviewer_technical) issues brief
		frappe.set_user("test_lead_1@example.com")
		item_lead = frappe.get_doc("Content Item", item.name)
		apply_workflow(item_lead, "Issue Brief")
		self.assertEqual(item_lead.workflow_state, "Briefed")

		# Lead can edit metadata
		item_lead.title = "Updated Title by Lead Reviewer"
		item_lead.save()
		self.assertEqual(item_lead.title, "Updated Title by Lead Reviewer")
		frappe.set_user("Administrator")

	def test_reviewer_workflow_review_actions(self):
		"""Ensures document reviewer can Request Changes and Approve, but cannot execute drafting actions."""
		from frappe.model.workflow import apply_workflow

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Reviewer Actions Test Item",
			"content_type": "Blog",
			"description": "Testing reviewer workflow actions.",
			"content_calendar": "2026 Test Calendar",
			"planned_publish_date": "2026-09-15",
			"due_date": "2026-09-01",
			"assigned_to": "test_writer_1@example.com",
			"reviewer_technical": "test_reviewer_1@example.com",
			"workflow_state": "Planned",
			"status": "Planned"
		})
		item.insert(ignore_permissions=True)

		# Advance properly to In Review
		apply_workflow(item, "Issue Brief")
		apply_workflow(item, "Start Work")
		item.content_file_1 = "/files/draft.pdf"
		item.save(ignore_permissions=True)
		apply_workflow(item, "Submit for Review")
		self.assertEqual(item.workflow_state, "In Review")

		# Reviewer requests changes with revision notes
		frappe.set_user("test_reviewer_1@example.com")
		item_rev = frappe.get_doc("Content Item", item.name)
		item_rev.revision_feedback_notes = "Please refine section 2."
		item_rev.save()
		apply_workflow(item_rev, "Request Changes")
		self.assertEqual(item_rev.workflow_state, "In Revision")

		# Reviewer CANNOT execute writer drafting actions
		self.assertRaises(frappe.PermissionError, apply_workflow, item_rev, "Resubmit Draft")

		# Writer resubmits draft
		frappe.set_user("test_writer_1@example.com")
		item_writer = frappe.get_doc("Content Item", item.name)
		apply_workflow(item_writer, "Resubmit Draft")
		self.assertEqual(item_writer.workflow_state, "In Progress")

		# Writer submits for review
		apply_workflow(item_writer, "Submit for Review")
		self.assertEqual(item_writer.workflow_state, "In Review")

		# Reviewer approves
		frappe.set_user("test_reviewer_1@example.com")
		item_rev2 = frappe.get_doc("Content Item", item.name)
		apply_workflow(item_rev2, "Approve")
		self.assertEqual(item_rev2.workflow_state, "Approved")
		frappe.set_user("Administrator")


