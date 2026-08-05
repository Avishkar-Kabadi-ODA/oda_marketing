// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.ui.form.on("Content Calendar", {
	refresh(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("View Content Items"), function() {
				frappe.set_route("List", "Content Item", { content_calendar: frm.doc.name });
			}, __("Actions"));
		}
	}
});
