# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import unittest
import frappe
from oda_marketing.oda_marketing.ai_engine.key_manager import get_secret
from oda_marketing.oda_marketing.ai_engine.file_extractor import extract_file_content, get_combined_draft_text
from oda_marketing.oda_marketing.ai_engine.prompt_subagent import generate_dynamic_system_prompt
from oda_marketing.oda_marketing.ai_engine.evaluator_agent import evaluate_content_item
from oda_marketing.oda_marketing.ai_engine.runner import run_ai_review


def _create_test_item(overrides=None):
	"""Helper to create a Content Item with sensible defaults, bypassing workflow validation."""
	defaults = {
		"doctype": "Content Item",
		"title": "Test Item",
		"content_type": "Blog",
		"topic": "Test topic for evaluation.",
		"practice_area": "Cross-domain",
		"content_calendar": "2026 Global Marketing Operations Calendar",
		"planned_publish_date": "2026-09-01",
		"assigned_to": "writer.test@oda.local",
		"reviewer_technical": "Avishkar.Kabadi@optimumdataanalytics.com",
	}
	if overrides:
		defaults.update(overrides)

	doc = frappe.get_doc(defaults)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_workflow = True
	doc.insert(ignore_permissions=True)
	return doc


def _set_workflow_state(doc, state):
	"""Helper to force-set workflow state bypassing Frappe workflow transition validation."""
	doc.db_set({
		"workflow_state": state,
		"status": state
	}, update_modified=False)
	doc.reload()
	return doc


class TestAIAgentEngine(unittest.TestCase):
	def setUp(self):
		frappe.db.rollback()
		cal_name = "2026 Global Marketing Operations Calendar"
		if not frappe.db.exists("Content Calendar", cal_name):
			frappe.get_doc({
				"doctype": "Content Calendar",
				"calendar_name": cal_name,
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"status": "Active"
			}).insert(ignore_permissions=True)

		# Ensure Content Item Option records exist
		for label in ["Blog", "Poll", "Flowchart", "Carousel"]:
			if not frappe.db.exists("Content Item Option", label):
				frappe.get_doc({
					"doctype": "Content Item Option",
					"option_type": "Format",
					"option_label": label,
					"is_active": 1
				}).insert(ignore_permissions=True)

		for label in ["HCLS", "Pharma Supply Chain", "Fintech", "Agriculture", "Cross-domain"]:
			if not frappe.db.exists("Content Item Option", label):
				frappe.get_doc({
					"doctype": "Content Item Option",
					"option_type": "Practice Area",
					"option_label": label,
					"is_active": 1
				}).insert(ignore_permissions=True)

		frappe.db.set_single_value("Marketing Settings", "enable_ai_copilot", 1)
		frappe.db.set_single_value("Marketing Settings", "ai_copilot_passing_score", 80)
		frappe.db.set_single_value("Marketing Settings", "max_copilot_reviews_per_item", 3)
		if hasattr(frappe.local, "single_docs"):
			frappe.local.single_docs.pop("Marketing Settings", None)
		frappe.clear_cache()

	def test_env_variable_decryption(self):
		"""Tests creation and retrieval of encrypted Env Variable keys."""
		if frappe.db.exists("Env Variable", "TEST_APIM_KEY"):
			frappe.delete_doc("Env Variable", "TEST_APIM_KEY", force=True)

		doc = frappe.get_doc({
			"doctype": "Env Variable",
			"variable_name": "TEST_APIM_KEY",
			"provider": "APIM Gateway",
			"value": "secret-apim-token-12345",
			"description": "Test subscription key"
		})
		doc.insert(ignore_permissions=True)

		retrieved_key = get_secret("TEST_APIM_KEY")
		self.assertEqual(retrieved_key, "secret-apim-token-12345")

	def test_subagent_dynamic_prompt_generation(self):
		"""Tests that the subagent generates a custom prompt based on deliverable metadata."""
		item = _create_test_item({
			"title": "Oncology AI Decision Support",
			"topic": "Evaluating LLM precision in oncology clinical trial matching.",
			"practice_area": "HCLS",
		})

		prompt = generate_dynamic_system_prompt(item)
		self.assertIn("Blog", prompt)
		self.assertIn("HCLS", prompt)
		self.assertTrue(len(prompt) > 50)

	def test_subagent_with_reviewer_instructions(self):
		"""Tests that reviewer instructions are incorporated into the generated prompt."""
		item = _create_test_item({
			"title": "Cloud Migration Guide",
			"topic": "AWS to Azure migration steps.",
		})

		instructions = "Focus on verifying the Terraform section accuracy."
		prompt = generate_dynamic_system_prompt(item, reviewer_instructions=instructions)
		self.assertIn("Terraform", prompt)

	def test_ai_score_does_not_block_transitions(self):
		"""Tests that AI score is informational only — does not block workflow transitions."""
		item = _create_test_item({
			"title": "Low Score Test Draft",
			"practice_area": "Fintech",
			"content_file_1": "/files/sample_draft.txt",
			"ai_score": 50,
			"ai_review_status": "Completed",
		})

		# Force to In Progress first, then to In Review
		_set_workflow_state(item, "Briefed")
		_set_workflow_state(item, "In Progress")

		# Should NOT throw — AI score no longer blocks transitions
		item.workflow_state = "In Review"
		item.flags.ignore_permissions = True
		item.flags.ignore_workflow = True
		item.save(ignore_permissions=True)
		self.assertEqual(item.workflow_state, "In Review")

	def test_full_ai_review_runner_flow(self):
		"""Tests full background runner execution — score is recorded but state is NOT auto-changed."""
		item = _create_test_item({
			"title": "Enterprise Cloud Migration Blueprint",
			"topic": "Step by step cloud migration guide for enterprise infrastructure.",
			"content_file_1": "/files/sample_draft.txt",
			"notes": "<p>Detailed cloud architecture document covering multi-cloud failover, Terraform automation, zero-trust network access, and cost governance.</p>",
		})

		# Force item into Marketing Copilot Review state
		_set_workflow_state(item, "Marketing Copilot Review")

		run_ai_review(item.name)

		updated_item = frappe.get_doc("Content Item", item.name)
		self.assertEqual(updated_item.ai_review_status, "Completed")
		self.assertTrue(updated_item.ai_score >= 0)
		self.assertTrue(len(updated_item.ai_copilot_feedback) > 10)
		self.assertTrue(len(updated_item.ai_generated_prompt) > 10)
		self.assertEqual(len(updated_item.ai_reviews), 1)

		# Run second AI review and verify thread history persists multiple entries
		run_ai_review(item.name)
		updated_item_2 = frappe.get_doc("Content Item", item.name)
		self.assertEqual(len(updated_item_2.ai_reviews), 2)

	def test_copilot_review_limit(self):
		"""Tests that max_copilot_reviews_per_item limit is enforced."""
		settings = frappe.get_single("Marketing Settings")
		settings.max_copilot_reviews_per_item = 2
		settings.save(ignore_permissions=True)
		if hasattr(frappe.local, "single_docs"):
			frappe.local.single_docs.pop("Marketing Settings", None)
		frappe.clear_cache()

		item = _create_test_item({
			"title": "Limit Test Item",
			"practice_area": "Fintech",
			"content_file_1": "/files/sample_draft.txt",
		})

		# Force item into Marketing Copilot Review state
		_set_workflow_state(item, "Marketing Copilot Review")

		# Run 2 reviews (within limit)
		run_ai_review(item.name)
		run_ai_review(item.name)

		updated_item = frappe.get_doc("Content Item", item.name)
		self.assertEqual(len(updated_item.ai_reviews), 2)

		# Third review should raise ValidationError
		with self.assertRaises(frappe.ValidationError):
			run_ai_review(item.name)

	def test_email_notifications_disabled(self):
		"""Tests that no email is sent when enable_email_notifications is unchecked."""
		frappe.db.set_single_value("Marketing Settings", "enable_email_notifications", 0)
		frappe.clear_cache()

		item = _create_test_item({
			"title": "Email Toggle Test Item",
			"practice_area": "HCLS",
		})

		from oda_marketing.oda_marketing.ai_engine.runner import notify_writer_copilot_failed
		frappe.flags.sent_mails = []
		notify_writer_copilot_failed(item, 50, "Failed feedback")
		self.assertEqual(len(getattr(frappe.flags, "sent_mails", [])), 0)

	def tearDown(self):
		frappe.db.rollback()
