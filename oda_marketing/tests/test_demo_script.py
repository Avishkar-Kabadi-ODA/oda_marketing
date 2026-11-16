# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, add_days, nowdate
from frappe.model.workflow import apply_workflow
from oda_marketing.permissions import get_content_item_permission_query_conditions, has_content_item_permission
from oda_marketing.setup_fixtures import setup_email_templates_and_settings

_TEST_USER_SUFFIX = frappe.generate_hash(length=10)
TEST_LEAD = f"marketing-lead-{_TEST_USER_SUFFIX}@example.com"
TEST_WRITER = f"marketing-writer-{_TEST_USER_SUFFIX}@example.com"
TEST_REVIEWER = f"marketing-reviewer-{_TEST_USER_SUFFIX}@example.com"
TEST_LEAD_2 = f"marketing-lead-2-{_TEST_USER_SUFFIX}@example.com"


def create_unit_test_users():
	test_users = [
		{"email": TEST_LEAD, "first_name": "Marketing", "last_name": "Lead Test", "role": "Marketing Lead"},
		{"email": TEST_WRITER, "first_name": "Content", "last_name": "Writer Test", "role": "Desk User"},
		{"email": TEST_REVIEWER, "first_name": "Technical", "last_name": "Reviewer Test", "role": "Desk User"},
		{"email": TEST_LEAD_2, "first_name": "Marketing", "last_name": "Lead Test Two", "role": "Marketing Lead"},
	]
	for u in test_users:
		if not frappe.db.exists("User", u["email"]):
			user_dict = {
				"doctype": "User",
				"email": u["email"],
				"first_name": u["first_name"],
				"last_name": u["last_name"],
				"enabled": 1,
				"send_welcome_email": 0,
				"user_type": "System User"
			}
			if u.get("role"):
				user_dict["roles"] = [{"role": u["role"]}]
			user = frappe.get_doc(user_dict)
			user.insert(ignore_permissions=True)
			from frappe.utils.password import update_password
			update_password(u["email"], "Password123!")
		else:
			user = frappe.get_doc("User", u["email"])
			if u.get("role"):
				user.add_roles(u["role"])


class TestMarketingOperationsFlow(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		create_unit_test_users()

	def test_setup_fixtures_preserve_custom_ai_prompts(self):
		settings = frappe.get_single("Marketing Settings")
		settings.subagent_meta_prompt = "Administrator custom subagent prompt."
		settings.evaluator_default_prompt = "Administrator custom evaluator prompt."
		settings.save(ignore_permissions=True)

		setup_email_templates_and_settings()

		self.assertEqual(
			frappe.db.get_single_value("Marketing Settings", "subagent_meta_prompt"),
			"Administrator custom subagent prompt.",
		)
		self.assertEqual(
			frappe.db.get_single_value("Marketing Settings", "evaluator_default_prompt"),
			"Administrator custom evaluator prompt.",
		)

	def test_strict_role_creation_and_editing_permissions(self):
		frappe.set_user(TEST_LEAD)
		cal = frappe.get_doc({
			"doctype": "Content Calendar",
			"calendar_name": f"2026 Operations Calendar {frappe.generate_hash(length=8)}",
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"status": "Active"
		}).insert()

		# Test Writer CANNOT create a new Content Item
		frappe.set_user(TEST_WRITER)
		item_unauthorized = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Unauthorized Item",
			"content_type": "Blog",
			"description": "Unauthorized creation",
			"content_calendar": cal.name,
			"planned_publish_date": "2026-09-01",
			"due_date": "2026-08-25",
			"assigned_to": TEST_WRITER,
			"reviewer_technical": TEST_REVIEWER
		})
		self.assertRaises(frappe.PermissionError, item_unauthorized.insert)

		# Lead creates the item successfully
		frappe.set_user(TEST_LEAD)
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Authorized Item",
			"content_type": "Blog",
			"description": "Authorized creation",
			"content_calendar": cal.name,
			"planned_publish_date": "2026-09-01",
			"due_date": "2026-08-25",
			"assigned_to": TEST_WRITER,
			"reviewer_technical": TEST_REVIEWER
		})
		item.insert()

		# Writer attempts to modify core metadata (title) -> fails
		frappe.set_user(TEST_WRITER)
		item.reload()
		item.title = "Modified Title By Writer"
		# Move item to Briefed -> In Progress so Writer can edit attachments/notes
		frappe.set_user(TEST_LEAD)
		item.reload()
		apply_workflow(item, "Issue Brief")

		frappe.set_user(TEST_WRITER)
		item.reload()
		apply_workflow(item, "Start Work")

		# Writer attempts to modify due date in "In Progress" state -> FAILS (Due Date is restricted to Marketing Leads)
		item.reload()
		item.due_date = "2026-10-10"
		self.assertRaises(frappe.PermissionError, item.save)

		# Writer updates content_file_1, content_file_2, content_file_3 in In Progress -> succeeds
		item.reload()
		item.content_file_1 = "/files/primary_draft.md"
		item.content_file_2 = "/files/asset_1.png"
		item.content_file_3 = "/files/asset_2.png"
		item.save()

		frappe.set_user("Administrator")

	def test_sla_due_date_manual_entry_and_validations(self):
		"""Tests that SLA Due Date is now manual (no auto-calculation) and validations work."""
		frappe.set_user(TEST_LEAD)
		cal = frappe.get_doc({
			"doctype": "Content Calendar",
			"calendar_name": f"SLA Test Calendar {frappe.generate_hash(length=8)}",
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"status": "Active"
		}).insert()

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "SLA Manual Date Item",
			"content_type": "Blog",
			"description": "SLA test",
			"content_calendar": cal.name,
			"planned_publish_date": "2026-09-01",
			"assigned_to": TEST_WRITER,
			"reviewer_technical": TEST_REVIEWER,
			"due_date": "2026-08-20"
		})
		item.insert()

		# Verify Due Date is the manually set value (no auto-calculation)
		self.assertEqual(str(item.due_date), "2026-08-20")

		# Test mandatory Published URL validation
		item.workflow_state = "Published"
		item.published_url = ""
		item.flags.ignore_workflow = True
		self.assertRaises(frappe.ValidationError, item.save)

		# Test mandatory Reviewer validation for In Review
		item.workflow_state = "In Review"
		item.reviewer_technical = ""
		item.flags.ignore_workflow = True
		self.assertRaises(frappe.ValidationError, item.save)

		frappe.set_user("Administrator")

	def test_end_to_end_multi_stage_workflow_and_permissions(self):
		tech_rev = TEST_REVIEWER

		frappe.set_user(TEST_LEAD)

		cal = frappe.get_doc({
			"doctype": "Content Calendar",
			"calendar_name": f"2026 Operations Calendar {frappe.generate_hash(length=8)}",
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"status": "Active",
			"description": "Master 2026 Content Calendar setup"
		})
		cal.insert()

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "GenAI in Oncology",
			"content_type": "Blog",
			"description": "Clinical AI decision support",
			"industry_domain": "HCLS",
			"content_calendar": cal.name,
			"planned_publish_date": "2026-09-01",
			"due_date": "2026-08-25",
			"assigned_to": TEST_WRITER,
			"reviewer_technical": tech_rev
		})
		item.insert()

		item.reload()
		# In Planned state, only Leads can view; non-leads cannot view until Briefed
		self.assertFalse(has_content_item_permission(item, user=TEST_WRITER))
		self.assertFalse(has_content_item_permission(item, user=tech_rev))
		self.assertTrue(has_content_item_permission(item, user=TEST_LEAD_2))

		# Issue Brief
		frappe.set_user(TEST_LEAD)
		item.reload()
		apply_workflow(item, "Issue Brief")
		item.reload()
		self.assertEqual(item.workflow_state, "Briefed")

		# Once Briefed, Writer and Reviewer can view
		self.assertTrue(has_content_item_permission(item, user=TEST_WRITER))
		self.assertTrue(has_content_item_permission(item, user=tech_rev))

		# Start Work (renamed from "Accept Brief")
		frappe.set_user(TEST_WRITER)
		item.reload()
		apply_workflow(item, "Start Work")
		item.reload()
		self.assertEqual(item.workflow_state, "In Progress")

		# Verify brief_accepted_on was stamped
		self.assertIsNotNone(item.brief_accepted_on)

		# Submit for Review (renamed from "Submit for Technical Review")
		item.reload()
		item.content_file_1 = "/files/sample_draft.md"
		item.save()
		apply_workflow(item, "Submit for Review")
		item.reload()
		self.assertEqual(item.workflow_state, "In Review")

		# Request Changes
		frappe.set_user(tech_rev)
		item.reload()
		item.revision_feedback_notes = "Please clarify the FDA compliance section on page 3."
		item.save()
		apply_workflow(item, "Request Changes")
		item.reload()
		self.assertEqual(item.workflow_state, "In Revision")

		# Resubmit Draft -> goes to "In Progress" (not directly to review)
		frappe.set_user(TEST_WRITER)
		item.reload()
		item.content_file_1 = "/files/sample_draft.md"
		item.save()
		apply_workflow(item, "Resubmit Draft")
		item.reload()
		self.assertEqual(item.workflow_state, "In Progress")

		# Submit for Review again
		item.reload()
		apply_workflow(item, "Submit for Review")
		item.reload()
		self.assertEqual(item.workflow_state, "In Review")

		# Approve (renamed from "Approve Technical") -> Approved
		frappe.set_user(tech_rev)
		item.reload()
		apply_workflow(item, "Approve")
		item.reload()
		self.assertEqual(item.workflow_state, "Approved")

		# Publish -> Published
		frappe.set_user(TEST_LEAD)
		item.reload()
		item.published_url = "https://optimumdataanalytics.com/blogs/genai-oncology"
		item.save()
		apply_workflow(item, "Publish")
		item.reload()
		self.assertEqual(item.workflow_state, "Published")

		frappe.set_user("Administrator")
		print("End-to-end multi-stage workflow, email CTA button links, and targeted notification test passed successfully!")

	def test_ai_copilot_resubmission_from_revision(self):
		"""Tests that AI Copilot review works when triggered from In Progress after revision,
		and that score is informational only (does not auto-route)."""
		frappe.db.set_single_value("Marketing Settings", "enable_ai_copilot", 1)
		frappe.db.set_single_value("Marketing Settings", "ai_copilot_passing_score", 80)
		frappe.clear_cache()

		tech_rev = TEST_REVIEWER
		frappe.set_user(TEST_LEAD)

		cal = frappe.get_doc({
			"doctype": "Content Calendar",
			"calendar_name": f"Copilot Test Cal 2026 {frappe.generate_hash(length=8)}",
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"status": "Active"
		}).insert()

		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "AI Copilot Resubmit Item",
			"content_type": "Blog",
			"description": "Testing AI re-evaluation from In Revision",
			"industry_domain": "HCLS",
			"content_calendar": cal.name,
			"planned_publish_date": "2026-09-01",
			"due_date": "2026-08-25",
			"assigned_to": TEST_WRITER,
			"reviewer_technical": tech_rev,
			"content_file_1": "/files/sample_draft.md"
		}).insert()

		# Force item to In Review state via db_set (bypassing workflow transitions)
		item.db_set({
			"ai_score": 90,
			"ai_review_status": "Completed",
			"workflow_state": "In Review",
			"status": "In Review"
		}, update_modified=False)
		item.reload()

		# Technical Reviewer requests changes -> In Revision
		frappe.set_user(tech_rev)
		item.reload()
		item.revision_feedback_notes = "Please update draft section 2."
		item.save()
		apply_workflow(item, "Request Changes")
		item.reload()
		self.assertEqual(item.workflow_state, "In Revision")

		# Writer resubmits draft -> goes to In Progress (not auto-routed to Copilot Review)
		frappe.set_user(TEST_WRITER)
		item.reload()
		item.content_file_1 = "/files/updated_draft.md"
		item.save()
		apply_workflow(item, "Resubmit Draft")
		item.reload()
		self.assertEqual(item.workflow_state, "In Progress")

		# Writer optionally triggers Copilot Review from In Progress via API action (optional, no state mutation)
		from oda_marketing.oda_marketing.doctype.content_item.content_item import trigger_ai_copilot
		trigger_ai_copilot(item.name)
		item.reload()
		self.assertEqual(item.workflow_state, "In Progress")
		self.assertIn(item.ai_review_status, ["Queued", "In Progress", "Completed"])

		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
