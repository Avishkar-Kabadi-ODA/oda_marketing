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
		for email, role in [("test_writer_1@example.com", "Content Writer"), ("test_reviewer_1@example.com", "Technical Reviewer"), ("test_lead_1@example.com", "Marketing Lead")]:
			if not frappe.db.exists("User", email):
				user = frappe.get_doc({
					"doctype": "User",
					"email": email,
					"first_name": email.split("@")[0],
					"enabled": 1,
					"user_type": "System User",
					"roles": [{"role": role}]
				})
				user.insert(ignore_permissions=True)

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
		"""Ensures a reviewer assigned as author gets treated strictly as Writer for that document."""
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
			"workflow_state": "Briefed",
			"status": "Briefed"
		})
		item.insert(ignore_permissions=True)

		effective_role = item.get_user_effective_role("test_reviewer_1@example.com")
		self.assertEqual(effective_role, "Writer")

		reviewer_role = item.get_user_effective_role("test_lead_1@example.com")
		self.assertEqual(reviewer_role, "Reviewer")

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

		test_file_path = "/tmp/test_content_import.xlsx"
		wb.save(test_file_path)

		res = import_content_items_from_excel(file_url=test_file_path, default_calendar="2026 Test Calendar")
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
		metrics = get_dashboard_metrics(calendar="2026 Test Calendar", year="2026", month="0")
		self.assertIn("kpis", metrics)
		self.assertIn("status_distribution", metrics)
		self.assertIn("format_distribution", metrics)
		self.assertIn("monthly_trend", metrics)
		self.assertGreaterEqual(metrics["kpis"]["total"], 1)
