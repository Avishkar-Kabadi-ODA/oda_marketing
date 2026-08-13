# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

"""
Patch: Rename workflow state "In Review - Technical" to "In Review" in all Content Item records,
Kanban Board columns, and related data.
"""

import frappe


def execute():
	# Update Content Item workflow_state and status fields
	frappe.db.sql("""
		UPDATE `tabContent Item`
		SET workflow_state = 'In Review'
		WHERE workflow_state = 'In Review - Technical'
	""")

	frappe.db.sql("""
		UPDATE `tabContent Item`
		SET status = 'In Review'
		WHERE status = 'In Review - Technical'
	""")

	# Update Kanban Board columns if they exist
	frappe.db.sql("""
		UPDATE `tabKanban Board Column`
		SET column_name = 'In Review'
		WHERE column_name = 'In Review - Technical'
		AND parent IN (
			SELECT name FROM `tabKanban Board`
			WHERE reference_doctype = 'Content Item'
		)
	""")

	# Update any Version / Comment references (best effort, non-critical)
	try:
		frappe.db.sql("""
			UPDATE `tabVersion`
			SET data = REPLACE(data, 'In Review - Technical', 'In Review')
			WHERE ref_doctype = 'Content Item'
			AND data LIKE '%In Review - Technical%'
		""")
	except Exception:
		pass

	frappe.db.commit()
	print("Patch: Renamed 'In Review - Technical' to 'In Review' in all Content Item records.")
