// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.listview_settings["Content Item"] = {
	add_fields: [
		"status", "workflow_state", "content_type", "assigned_to",
		"reviewer_technical", "content_calendar", "planned_publish_date", "due_date", "risk_flag"
	],

	get_indicator(doc) {
		const state = doc.workflow_state || doc.status || "Planned";
		const colors = {
			"Planned": "gray",
			"Briefed": "blue",
			"In Progress": "orange",
			"In Review": "yellow",
			"In Revision": "red",
			"Approved": "cyan",
			"Published": "green"
		};
		return [__(state), colors[state] || "gray", `workflow_state,=,${state}`];
	},

	onload(listview) {
		const is_lead = frappe.user.has_role("Marketing Lead") || frappe.user.has_role("System Manager") || frappe.session.user === "Administrator";

		if (is_lead) {
			listview.page.add_button(__("Import from Excel"), function() {
				show_excel_import_dialog(listview);
			}, "octicon octicon-file-symlink-file");

			listview.page.add_menu_item(__("Download Excel Template"), function() {
				window.open("/api/method/oda_marketing.oda_marketing.doctype.content_item.content_item.download_content_item_template");
			});
		}
	}
};

function show_excel_import_dialog(listview) {
	let dialog = new frappe.ui.Dialog({
		title: __("Bulk Import Content Items from Excel / CSV"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "help_html",
				options: `
					<div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px;">
						<div style="font-weight: 600; color: #1E293B; margin-bottom: 4px; font-size: 13px;">
							<i class="octicon octicon-info" style="color: #4F46E5; margin-right: 6px;"></i> Import Instructions
						</div>
						<div style="color: #64748B; font-size: 12px; line-height: 1.5;">
							• Upload your <code>.xlsx</code> or <code>.csv</code> spreadsheet with deliverable details.<br>
							• All imported items will start in <b>Planned</b> status by default.<br>
							• Assigned writers cannot see items until briefs are issued.
						</div>
						<div style="margin-top: 10px;">
							<a href="/api/method/oda_marketing.oda_marketing.doctype.content_item.content_item.download_content_item_template" target="_blank" class="btn btn-xs btn-default" style="font-weight: 600; color: #4F46E5;">
								<i class="octicon octicon-download"></i> Download Excel Template (.xlsx)
							</a>
						</div>
					</div>
				`
			},
			{
				label: __("Default Content Calendar"),
				fieldname: "default_calendar",
				fieldtype: "Link",
				options: "Content Calendar",
				description: __("Optional fallback calendar if a row in your spreadsheet does not specify one.")
			},
			{
				label: __("Upload Spreadsheet (.xlsx or .csv)"),
				fieldname: "spreadsheet_file",
				fieldtype: "Attach",
				reqd: 1,
				description: __("Attach your filled spreadsheet file.")
			}
		],
		primary_action_label: __("Start Import"),
		primary_action(values) {
			if (!values.spreadsheet_file) {
				frappe.msgprint(__("Please attach an Excel or CSV spreadsheet first."));
				return;
			}

			const primary_btn = dialog.get_primary_btn();
			if (primary_btn) {
				primary_btn.prop("disabled", true).text(__("Importing..."));
			}
			dialog.hide();

			frappe.call({
				method: "oda_marketing.oda_marketing.doctype.content_item.content_item.import_content_items_from_excel",
				args: {
					file_url: values.spreadsheet_file,
					default_calendar: values.default_calendar || null
				},
				freeze: true,
				freeze_message: __("Importing Content Items... Parsing spreadsheet and creating deliverables."),
				callback(r) {
					try {
						if (frappe.hide_progress) frappe.hide_progress();
						frappe.cur_progress = null;
						$(".modal.progress-modal").modal("hide").remove();
						$(".modal-backdrop").not(".msgprint-dialog ~ .modal-backdrop").remove();
					} catch (e) {
						// ignore
					}

					if (r && r.message) {
						const res = r.message;
						let msg = `<div style="font-size: 13px;">`;
						msg += `<p style="color: #059669; font-weight: 600; font-size: 14px;">✓ Successfully imported <b>${res.created_count}</b> content deliverable(s) into <b>Planned</b> status.</p>`;

						if (res.error_count > 0) {
							msg += `<p style="color: #DC2626; font-weight: 600; margin-top: 10px;">⚠️ ${res.error_count} row(s) had errors and were skipped:</p><ul style="max-height: 150px; overflow-y: auto; padding-left: 18px; color: #475569;">`;
							res.errors.forEach(err => {
								msg += `<li><b>Row ${err.row} (${err.title}):</b> ${err.errors.join(", ")}</li>`;
							});
							msg += `</ul>`;
						}

						msg += `</div>`;

						frappe.msgprint({
							title: __("Import Summary"),
							message: msg,
							indicator: res.created_count > 0 ? "green" : "red"
						});

						listview.refresh();
					}
				},
				error(err) {
					try {
						if (frappe.hide_progress) frappe.hide_progress();
						frappe.cur_progress = null;
						$(".modal.progress-modal").modal("hide").remove();
					} catch (e) {
						// ignore
					}
					if (primary_btn) {
						primary_btn.prop("disabled", false).text(__("Start Import"));
					}
				}
			});
		}
	});

	dialog.show();
}
