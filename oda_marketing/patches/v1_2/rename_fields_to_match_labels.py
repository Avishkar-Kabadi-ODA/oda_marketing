# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doctype("Content Item")
	frappe.reload_doctype("Marketing Settings")

	if frappe.db.has_column("Content Item", "topic"):
		try:
			rename_field("Content Item", "topic", "description")
		except Exception:
			pass

	if frappe.db.has_column("Content Item", "practice_area"):
		try:
			rename_field("Content Item", "practice_area", "industry_domain")
		except Exception:
			pass

	if frappe.db.has_column("Content Item", "sla_due_date"):
		try:
			rename_field("Content Item", "sla_due_date", "due_date")
		except Exception:
			pass

	try:
		frappe.db.sql("""
			UPDATE `tabSingles`
			SET field = 'overdue_email_template'
			WHERE doctype = 'Marketing Settings' AND field = 'overdue_sla_email_template'
		""")
	except Exception:
		pass
