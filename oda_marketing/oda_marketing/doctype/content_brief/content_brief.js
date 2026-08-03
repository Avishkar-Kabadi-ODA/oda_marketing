// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.ui.form.on("Content Brief", {
	onload(frm) {
		// Filter content_item dropdown to show ONLY Content Items that do not have a brief linked yet
		frm.set_query("content_item", function() {
			return {
				filters: {
					"content_brief": ["in", ["", null]]
				}
			};
		});
	},
	after_save(frm) {
		if (frm.doc.content_item) {
			frappe.show_alert({
				message: __("Content Brief saved and linked to Content Item."),
				indicator: "green"
			}, 3);
			// Automatically route back to the linked Content Item form
			frappe.set_route("Form", "Content Item", frm.doc.content_item);
		}
	}
});
