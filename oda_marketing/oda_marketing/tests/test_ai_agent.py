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
		cal_name = "2026 Global Marketing Operations Calendar"
		if not frappe.db.exists("Content Calendar", cal_name):
			frappe.get_doc({
				"doctype": "Content Calendar",
				"calendar_name": cal_name,
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"status": "Active"
			}).insert(ignore_permissions=True)

		frappe.db.set_single_value("Marketing Settings", "enable_ai_copilot", 1)
		frappe.db.set_single_value("Marketing Settings", "ai_copilot_passing_score", 80)
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
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Oncology AI Decision Support",
			"content_type": "Blog",
			"topic": "Evaluating LLM precision in oncology clinical trial matching.",
			"practice_area": "HCLS",
			"content_calendar": "2026 Global Marketing Operations Calendar",
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local",
			"reviewer_technical": "Avishkar.Kabadi@optimumdataanalytics.com"
		})
		item.insert(ignore_permissions=True)

		prompt = generate_dynamic_system_prompt(item)
		self.assertIn("Blog", prompt)
		self.assertIn("HCLS", prompt)
		self.assertTrue(len(prompt) > 50)

	def test_gatekeeper_validation_prevents_manual_bypass(self):
		"""Tests that Content Item validation prevents manually skipping to Technical Review when score < passing score."""
		item = frappe.get_doc({
			"doctype": "Content Item",
			"title": "Incomplete Test Draft",
			"content_type": "Blog",
			"topic": "Brief draft topic",
			"practice_area": "Fintech",
			"content_calendar": "2026 Global Marketing Operations Calendar",
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local",
			"reviewer_technical": "Avishkar.Kabadi@optimumdataanalytics.com",
			"content_file_1": "/files/sample_draft.txt",
			"ai_score": 50,
			"ai_review_status": "Completed"
		})
		item.insert(ignore_permissions=True)

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
			"content_calendar": "2026 Global Marketing Operations Calendar",
			"planned_publish_date": "2026-09-01",
			"assigned_to": "writer.test@oda.local",
			"reviewer_technical": "Avishkar.Kabadi@optimumdataanalytics.com",
			"content_file_1": "/files/sample_draft.txt",
			"notes": "<p>Detailed cloud architecture document covering multi-cloud failover, Terraform automation, zero-trust network access, and cost governance.</p>"
		})
		item.insert(ignore_permissions=True)

		run_ai_review(item.name)

		updated_item = frappe.get_doc("Content Item", item.name)
		self.assertEqual(updated_item.ai_review_status, "Completed")
		self.assertTrue(updated_item.ai_score >= 0)
		self.assertTrue(len(updated_item.ai_copilot_feedback) > 10)
		self.assertTrue(len(updated_item.ai_generated_prompt) > 10)

		settings = frappe.get_single("Marketing Settings")
		passing = int(getattr(settings, "ai_copilot_passing_score", 80) or 80)

		if updated_item.ai_score < passing:
			self.assertEqual(updated_item.workflow_state, "In Revision")
		else:
			self.assertEqual(updated_item.workflow_state, "In Review - Technical")

	def tearDown(self):
		frappe.db.rollback()
