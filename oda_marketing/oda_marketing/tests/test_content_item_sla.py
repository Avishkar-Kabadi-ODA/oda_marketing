# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from oda_marketing.oda_marketing.doctype.content_item.content_item import (
	ContentItem,
	is_business_hour,
)


class TestContentItemSLA(unittest.TestCase):
	def test_due_date_cannot_be_later_than_publish_date(self):
		item = ContentItem({
			"doctype": "Content Item",
			"due_date": "2026-09-02",
			"planned_publish_date": "2026-09-01",
		})
		with self.assertRaises(frappe.ValidationError):
			item.validate_due_date_with_publish_date()

	def test_equal_due_and_publish_dates_are_valid(self):
		item = ContentItem({
			"doctype": "Content Item",
			"due_date": "2026-09-01",
			"planned_publish_date": "2026-09-01",
		})
		item.validate_due_date_with_publish_date()

	def test_stale_late_flag_is_cleared_after_due_date_moves(self):
		item = ContentItem({
			"doctype": "Content Item",
			"due_date": "2999-09-01",
			"workflow_state": "In Progress",
			"risk_flag": "Late",
		})
		with patch.object(
			frappe,
			"get_single",
			return_value=SimpleNamespace(enable_auto_overdue_flag=1),
		):
			item.check_overdue_sla()
		self.assertEqual(item.risk_flag, "On track")

	def test_business_hour_window_is_start_inclusive_and_end_exclusive(self):
		self.assertFalse(is_business_hour(8, 9, 19))
		self.assertTrue(is_business_hour(9, 9, 19))
		self.assertTrue(is_business_hour(18, 9, 19))
		self.assertFalse(is_business_hour(19, 9, 19))
