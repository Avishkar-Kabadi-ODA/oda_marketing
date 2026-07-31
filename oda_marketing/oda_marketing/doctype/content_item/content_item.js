// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.ui.form.on("Content Item", {
	refresh(frm) {
		if (frm.doc.content_brief) {
			frm.add_custom_button(__("View Content Brief"), function() {
				frappe.set_route("Form", "Content Brief", frm.doc.content_brief);
			}, __("Actions"));
		}
		if (frm.doc.content_calendar) {
			frm.add_custom_button(__("View Content Calendar"), function() {
				frappe.set_route("Form", "Content Calendar", frm.doc.content_calendar);
			}, __("Actions"));
		}
	}
});
