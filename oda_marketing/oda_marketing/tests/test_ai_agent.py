# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import unittest
import frappe
from oda_marketing.oda_marketing.ai_engine.key_manager import get_secret
from oda_marketing.oda_marketing.ai_engine.file_extractor import extract_file_content, get_combined_draft_text
from oda_marketing.oda_marketing.ai_engine.prompt_subagent import generate_dynamic_system_prompt
from oda_marketing.oda_marketing.ai_engine.evaluator_agent import evaluate_content_item
from oda_marketing.oda_marketing.ai_engine.runner import run_ai_review


class TestAIAgentEngine(unittest.TestCase):
	def setUp(self):
		frappe.db.rollback()

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
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Oncology AI Decision Support",
			"content_type": "Blog",
			"topic": "Evaluating LLM precision in oncology clinical trial matching.",
			"practice_area": "HCLS",
			"content_calendar": frappe.db.get_value("Content Calendar", {"status": "Active"}, "name") or "2026 Global Marketing Operations Calendar",
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local"
		})
		item.insert(ignore_permissions=True)

		prompt = generate_dynamic_system_prompt(item)
		self.assertIn("Blog", prompt)
		self.assertIn("HCLS", prompt)
		self.assertTrue(len(prompt) > 50)

	def test_gatekeeper_validation_prevents_manual_bypass(self):
		"""Tests that Content Item validation prevents manually skipping to Technical Review when score < 90%."""
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Incomplete Test Draft",
			"content_type": "Blog",
			"topic": "Brief draft topic",
			"practice_area": "Fintech",
			"content_calendar": frappe.db.get_value("Content Calendar", {"status": "Active"}, "name") or "2026 Global Marketing Operations Calendar",
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local",
			"ai_score": 75,
			"ai_review_status": "Completed"
		})
		item.insert(ignore_permissions=True)

		# Attempt manual transition to Technical Review with score 75%
		item.workflow_state = "In Review - Technical"
		with self.assertRaises(frappe.ValidationError):
			item.save(ignore_permissions=True)

	def test_full_ai_review_runner_flow(self):
		"""Tests full background runner execution and automatic state branching."""
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Enterprise Cloud Migration Blueprint",
			"content_type": "Blog",
			"topic": "Step by step cloud migration guide for enterprise infrastructure.",
			"practice_area": "Cross-domain",
			"content_calendar": frappe.db.get_value("Content Calendar", {"status": "Active"}, "name") or "2026 Global Marketing Operations Calendar",
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local",
			"notes": "<p>Detailed cloud architecture document covering multi-cloud failover, Terraform automation, zero-trust network access, and cost governance.</p>"
		})
		item.insert(ignore_permissions=True)

		# Run AI review background job synchronously for testing
		run_ai_review(item.name)

		# Reload item from DB
		updated_item = frappe.get_doc("Content Item", item.name)
		self.assertEqual(updated_item.ai_review_status, "Completed")
		self.assertTrue(updated_item.ai_score >= 0)
		self.assertTrue(len(updated_item.ai_copilot_feedback) > 10)
		self.assertTrue(len(updated_item.ai_generated_prompt) > 10)

		if updated_item.ai_score < 90:
			self.assertEqual(updated_item.workflow_state, "In Revision")
		else:
			self.assertEqual(updated_item.workflow_state, "In Review - Technical")

	def tearDown(self):
		frappe.db.rollback()
