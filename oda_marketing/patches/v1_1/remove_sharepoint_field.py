# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

"""
Patch: Remove the sharepoint_folder_url field from Content Item.
Drops the database column safely after nulling out any existing data.
"""

import frappe


def execute():
	# Null out any existing values first (preserve data in Version history)
	if frappe.db.has_column("Content Item", "sharepoint_folder_url"):
		frappe.db.sql("""
			UPDATE `tabContent Item`
			SET sharepoint_folder_url = NULL
			WHERE sharepoint_folder_url IS NOT NULL
		""")

		# Drop the column
		try:
			frappe.db.sql_ddl("ALTER TABLE `tabContent Item` DROP COLUMN `sharepoint_folder_url`")
			print("Patch: Dropped sharepoint_folder_url column from Content Item.")
		except Exception as e:
			# Column may not exist in fresh installations
			print(f"Patch: sharepoint_folder_url column drop skipped (may not exist): {str(e)}")

	# Remove any Custom Field records if they exist
	if frappe.db.exists("Custom Field", {"dt": "Content Item", "fieldname": "sharepoint_folder_url"}):
		frappe.delete_doc("Custom Field", {"dt": "Content Item", "fieldname": "sharepoint_folder_url"}, force=True)

	frappe.db.commit()
	print("Patch: SharePoint field removal completed.")
