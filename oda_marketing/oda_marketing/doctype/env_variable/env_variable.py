# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password


class EnvVariable(Document):
	def get_password_value(self):
		"""Safely retrieve decrypted password value from DB."""
		try:
			return get_decrypted_password("Env Variable", self.name, fieldname="value")
		except Exception:
			return getattr(self, "value", None)


@frappe.whitelist()
def get_env_var(variable_name, default=None):
	"""Utility helper to fetch decrypted environment variable value by name."""
	if frappe.db.exists("Env Variable", variable_name):
		doc = frappe.get_doc("Env Variable", variable_name)
		val = doc.get_password_value()
		if val:
			return val

	# Fallback to system environment variable
	import os
	return os.environ.get(variable_name, default)
