# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doctype("Content Item")
	frappe.reload_doctype("Marketing Settings")

	raw_cols = [c[0] for c in frappe.db.sql("SHOW COLUMNS FROM `tabContent Item`")]

	if "topic" in raw_cols and "description" not in raw_cols:
		rename_field("Content Item", "topic", "description")
	elif "topic" in raw_cols and "description" in raw_cols:
		frappe.db.sql("UPDATE `tabContent Item` SET description = topic WHERE (description IS NULL OR description = '') AND (topic IS NOT NULL AND topic != '')")
		frappe.db.commit()
		frappe.db.sql_ddl("ALTER TABLE `tabContent Item` DROP COLUMN topic")

	if "practice_area" in raw_cols and "industry_domain" not in raw_cols:
		rename_field("Content Item", "practice_area", "industry_domain")
	elif "practice_area" in raw_cols and "industry_domain" in raw_cols:
		frappe.db.sql("UPDATE `tabContent Item` SET industry_domain = practice_area WHERE (industry_domain IS NULL OR industry_domain = '') AND (practice_area IS NOT NULL AND practice_area != '')")
		frappe.db.commit()
		frappe.db.sql_ddl("ALTER TABLE `tabContent Item` DROP COLUMN practice_area")

	if "sla_due_date" in raw_cols and "due_date" not in raw_cols:
		rename_field("Content Item", "sla_due_date", "due_date")
	elif "sla_due_date" in raw_cols and "due_date" in raw_cols:
		frappe.db.sql("UPDATE `tabContent Item` SET due_date = sla_due_date WHERE due_date IS NULL AND sla_due_date IS NOT NULL")
		frappe.db.commit()
		frappe.db.sql_ddl("ALTER TABLE `tabContent Item` DROP COLUMN sla_due_date")

	try:
		frappe.db.sql("""
			UPDATE `tabSingles`
			SET field = 'overdue_email_template'
			WHERE doctype = 'Marketing Settings' AND field = 'overdue_sla_email_template'
		""")
	except Exception:
		pass
