# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

"""
Patch: Create Content Item Option records from existing hardcoded Select values
and migrate existing Content Item data to reference the new Link field records.
"""

import frappe


def execute():
	# Create Format options from old content_type Select values
	format_options = ["Blog", "Poll", "Flowchart", "Carousel"]
	for idx, label in enumerate(format_options):
		if not frappe.db.exists("Content Item Option", label):
			frappe.get_doc({
				"doctype": "Content Item Option",
				"option_type": "Format",
				"option_label": label,
				"is_active": 1,
				"sort_order": idx
			}).insert(ignore_permissions=True)

	# Create Industry Domain options from old practice_area Select values
	practice_area_options = ["HCLS", "Pharma Supply Chain", "Fintech", "Agriculture", "Cross-domain"]
	for idx, label in enumerate(practice_area_options):
		if not frappe.db.exists("Content Item Option", label):
			frappe.get_doc({
				"doctype": "Content Item Option",
				"option_type": "Industry Domain",
				"option_label": label,
				"is_active": 1,
				"sort_order": idx
			}).insert(ignore_permissions=True)

	# Migrate existing Content Item records:
	# content_type and practice_area fields now store Link references (the option_label value)
	# Since we're using autoname: field:option_label, the document name IS the option_label.
	# Old Select values like "Blog" now directly match the new Content Item Option name "Blog".
	# So existing data is already compatible — no UPDATE needed for records whose values
	# match the created options.

	# However, check for any non-standard values that don't match our predefined options
	# and create them as active options to prevent data loss.
	existing_content_types = frappe.db.sql_list(
		"SELECT DISTINCT content_type FROM `tabContent Item` WHERE content_type IS NOT NULL AND content_type != ''"
	)
	for ct in existing_content_types:
		if ct and not frappe.db.exists("Content Item Option", ct):
			frappe.get_doc({
				"doctype": "Content Item Option",
				"option_type": "Format",
				"option_label": ct,
				"is_active": 1,
				"sort_order": 99
			}).insert(ignore_permissions=True)
			print(f"Created Content Item Option for unmapped Format value: {ct}")

	existing_practice_areas = frappe.db.sql_list(
		"SELECT DISTINCT practice_area FROM `tabContent Item` WHERE practice_area IS NOT NULL AND practice_area != ''"
	)
	for pa in existing_practice_areas:
		if pa and not frappe.db.exists("Content Item Option", pa):
			frappe.get_doc({
				"doctype": "Content Item Option",
				"option_type": "Practice Area",
				"option_label": pa,
				"is_active": 1,
				"sort_order": 99
			}).insert(ignore_permissions=True)
			print(f"Created Content Item Option for unmapped Practice Area value: {pa}")

	frappe.db.commit()
	print("Patch: Content Item Options created and data migrated successfully.")
