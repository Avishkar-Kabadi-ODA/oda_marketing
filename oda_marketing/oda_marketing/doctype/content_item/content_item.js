// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.ui.form.on("Content Item", {
	setup(frm) {
		frm.set_query("content_type", function() {
			return {
				filters: {
					option_type: "Format",
					is_active: 1
				}
			};
		});

		frm.set_query("industry_domain", function() {
			return {
				filters: {
					option_type: "Industry Domain",
					is_active: 1
				}
			};
		});

		frm.set_query("reviewer_technical", function() {
			return {
				query: "oda_marketing.oda_marketing.doctype.content_item.content_item.get_reviewer_users",
				filters: {
					assigned_to: frm.doc.assigned_to || ""
				}
			};
		});

		frm.set_query("assigned_to", function() {
			return {
				query: "oda_marketing.oda_marketing.doctype.content_item.content_item.get_assigned_to_users",
				filters: {
					reviewer_technical: frm.doc.reviewer_technical || ""
				}
			};
		});
	},

	refresh(frm) {
		frm.trigger("apply_role_field_permissions");
		frm.trigger("filter_workflow_actions");
		frm.trigger("update_description_inline_counter");

		if (frm.doc.content_calendar) {
			frm.add_custom_button(__("View Content Calendar"), function() {
				frappe.set_route("Form", "Content Calendar", frm.doc.content_calendar);
			}, __("Navigate"));
		}

		frappe.call({
			method: "oda_marketing.oda_marketing.doctype.content_item.content_item.get_ai_copilot_status",
			callback: function(res) {
				const enable_ai = res && res.message ? res.message.enable_ai_copilot : 0;
				const max_writer_reviews = res && res.message ? res.message.max_writer_copilot_reviews_per_item : 2;
				const max_reviewer_reviews = res && res.message ? res.message.max_reviewer_copilot_reviews_per_item : 2;

				const current_user = (frappe.session.user || "").toLowerCase();
				const doc_assigned = (frm.doc.assigned_to || "").toLowerCase();
				const doc_reviewer = (frm.doc.reviewer_technical || "").toLowerCase();

				const is_doc_writer = (current_user === doc_assigned);
				const is_doc_reviewer = (current_user === doc_reviewer);
				const is_global_lead = frappe.user.has_role("Marketing Lead") || frappe.user.has_role("System Manager") || frappe.session.user === "Administrator";
				const is_lead = is_global_lead && !is_doc_writer;

				const has_primary_draft = !!(frm.doc.content_file_1 && String(frm.doc.content_file_1).trim());

				if (enable_ai) {
					// Ensure AI section and core AI fields are visible when AI Copilot is enabled
					frm.set_df_property("ai_section", "hidden", 0);
					frm.set_df_property("ai_score", "hidden", 0);
					frm.set_df_property("ai_review_status", "hidden", 0);

					// Copilot buttons require Primary Content Draft (content_file_1) to be attached
					if (has_primary_draft) {
						// Writer: show Run AI Copilot button when in active writing states (In Progress, In Revision, Briefed)
						const writer_copilot_states = ["In Progress", "In Revision", "Briefed"];
						const writer_reviews = (frm.doc.ai_reviews || []).filter(r => r.review_type === "Writer");
						const writer_limit_reached = writer_reviews.length >= max_writer_reviews;

						if ((writer_copilot_states.includes(frm.doc.workflow_state) || frm.doc.ai_review_status === "Queued") && (is_doc_writer || is_lead)) {
							if (!writer_limit_reached) {
								frm.add_custom_button(__("Run AI Copilot Review"), function() {
									frappe.show_progress(__("Marketing Copilot Review"), 10, 100, __("Initiating AI Copilot Review..."));
									frappe.call({
										method: "oda_marketing.oda_marketing.doctype.content_item.content_item.trigger_ai_copilot",
										args: { docname: frm.doc.name },
										callback: function(r) {
											frappe.show_progress(__("Marketing Copilot Review"), 20, 100, __("Evaluating content deliverable with AI Copilot..."));
										}
									});
								}, __("Copilot"));
							}
						}

						// Reviewer: show Run Copilot Review button when in "In Review" state
						const reviewer_reviews = (frm.doc.ai_reviews || []).filter(r => r.review_type === "Reviewer");
						const reviewer_limit_reached = reviewer_reviews.length >= max_reviewer_reviews;

						if ((is_doc_reviewer || (is_lead && !is_doc_writer)) && frm.doc.workflow_state === "In Review") {
							if (!reviewer_limit_reached) {
								frm.add_custom_button(__("Run Copilot Review (Reviewer)"), function() {
									let d = new frappe.ui.Dialog({
										title: __("Reviewer Copilot Instructions"),
										fields: [
											{
												label: __("Instructions for AI Copilot"),
												fieldname: "instructions",
												fieldtype: "Small Text",
												reqd: 1,
												description: __("Provide specific evaluation instructions for the AI Copilot (e.g., 'Check technical accuracy of the AWS migration section').")
											}
										],
										primary_action_label: __("Run Copilot Review"),
										primary_action(values) {
											d.hide();
											setTimeout(function() {
												frappe.show_progress(__("Marketing Copilot Review"), 10, 100, __("Initiating Reviewer Copilot Review..."));
												frappe.call({
													method: "oda_marketing.oda_marketing.doctype.content_item.content_item.trigger_reviewer_copilot",
													args: {
														docname: frm.doc.name,
														instructions: values.instructions
													},
													callback: function(r) {
														frappe.show_progress(__("Marketing Copilot Review"), 20, 100, __("Evaluating content deliverable with Reviewer Copilot..."));
													}
												});
											}, 200);
										}
									});
									d.show();
								}, __("Copilot"));
							}
						}
					}
				} else {
					// Hide AI section and evaluation fields when AI Copilot is disabled
					frm.set_df_property("ai_section", "hidden", 1);
					frm.set_df_property("ai_score", "hidden", 1);
					frm.set_df_property("ai_review_status", "hidden", 1);
					frm.set_df_property("writer_copilot_feedback", "hidden", 1);
					frm.set_df_property("reviewer_copilot_feedback", "hidden", 1);
					frm.set_df_property("ai_reviews", "hidden", 1);
				}
				frm.trigger("apply_role_field_permissions");
			}
		});

		// Listen for realtime streaming socket events from AI Agent (re-bound cleanly on every refresh)
		frappe.realtime.off("ai_copilot_stream");
		frappe.realtime.on("ai_copilot_stream", function(data) {
			if (data && data.docname === frm.doc.name) {
				if (data.progress >= 100) {
					frappe.show_progress(__("Marketing Copilot Review"), 100, 100, data.message || __("Review complete!"));
					setTimeout(() => {
						try {
							frappe.hide_progress();
							frappe.cur_progress = null;
							$(".modal.progress-modal").modal("hide").remove();
						} catch (e) {}
						frappe.show_alert({ message: __("AI Copilot Review completed!"), indicator: "green" });
						frm.reload_doc().then(() => {
							frm.trigger("apply_role_field_permissions");
							frm.refresh_fields();
						});
					}, 600);
				} else if (data.progress === 0 && (data.message || "").includes("failed")) {
					try {
						frappe.hide_progress();
						frappe.cur_progress = null;
						$(".modal.progress-modal").modal("hide").remove();
					} catch (e) {}
					frappe.show_alert({ message: data.message, indicator: "red" });
				} else {
					frappe.show_progress(__("Marketing Copilot Review"), data.progress || 50, 100, data.message || __("Evaluating deliverable..."));
				}
			}
		});
	},

	apply_role_field_permissions(frm) {
		const current_user = (frappe.session.user || "").toLowerCase();
		const doc_assigned = (frm.doc.assigned_to || "").toLowerCase();
		const doc_reviewer = (frm.doc.reviewer_technical || "").toLowerCase();

		const is_doc_writer = (current_user === doc_assigned);
		const is_doc_reviewer = (current_user === doc_reviewer);
		const is_global_lead = frappe.user.has_role("Marketing Lead") || frappe.user.has_role("System Manager") || frappe.session.user === "Administrator";
		const is_lead = is_global_lead && !is_doc_writer;

		if (!is_lead) {
			const metadata_fields = [
				"title", "content_type", "description", "industry_domain",
				"content_calendar", "planned_publish_date", "assigned_to",
				"reviewer_technical", "published_url", "risk_flag"
			];
			metadata_fields.forEach(field => frm.set_df_property(field, "read_only", 1));

			// Due Date is editable by Content Writer
			if (is_doc_writer || (!is_doc_reviewer && !is_lead)) {
				frm.set_df_property("due_date", "read_only", 0);
			}

			setTimeout(() => {
				$("a:contains('Edit Sidebar'), .sidebar-item-container:contains('Edit Sidebar')").hide();
			}, 300);
		}

		// Writer read-only enforcement before In Progress state
		const is_before_inprogress = ["Planned", "Briefed"].includes(frm.doc.workflow_state);

		if (is_doc_writer && !is_lead) {
			// Effective role is Writer on this document
			frm.set_df_property("content_file_1", "read_only", is_before_inprogress ? 1 : 0);
			frm.set_df_property("content_file_2", "read_only", is_before_inprogress ? 1 : 0);
			frm.set_df_property("content_file_3", "read_only", is_before_inprogress ? 1 : 0);
			frm.set_df_property("notes", "read_only", is_before_inprogress ? 1 : 0);
			frm.set_df_property("revision_feedback_notes", "read_only", 1);

			// Strictly hide Reviewer Instructions from Writer
			frm.set_df_property("reviewer_copilot_instructions", "hidden", 1);
		} else if (is_doc_reviewer && !is_lead) {
			// Effective role is Reviewer on this document
			frm.set_df_property("content_file_1", "read_only", 1);
			frm.set_df_property("content_file_2", "read_only", 1);
			frm.set_df_property("content_file_3", "read_only", 1);
			frm.set_df_property("notes", "read_only", 1);
			frm.set_df_property("revision_feedback_notes", "read_only", 0);
			frm.set_df_property("reviewer_copilot_instructions", "read_only", frm.doc.workflow_state === "In Review" ? 0 : 1);
			frm.set_df_property("reviewer_copilot_instructions", "hidden", (frm.doc.reviewer_copilot_instructions || frm.doc.workflow_state === "In Review") ? 0 : 1);
		} else if (is_lead) {
			frm.set_df_property("reviewer_copilot_instructions", "hidden", frm.doc.reviewer_copilot_instructions ? 0 : 1);
		}

		// Require revision feedback notes if state is In Revision
		if (frm.doc.workflow_state === "In Revision") {
			frm.set_df_property("revision_feedback_notes", "reqd", 1);
		}

		// Hidden for all users on form view (viewable in Marketing Settings)
		frm.set_df_property("ai_generated_prompt", "hidden", 1);

		// Always keep AI reviews table grid read-only to prevent user edits
		frm.set_df_property("ai_reviews", "read_only", 1);

		const writer_reviews = (frm.doc.ai_reviews || []).filter(r => r.review_type === "Writer");
		const reviewer_reviews = (frm.doc.ai_reviews || []).filter(r => r.review_type === "Reviewer");

		if (is_doc_reviewer && !is_lead) {
			// Reviewer sees ONLY Reviewer feedback & Reviewer reviews; STRICTLY HIDE Writer feedback
			frm.set_df_property("reviewer_copilot_feedback", "hidden", (frm.doc.reviewer_copilot_feedback || reviewer_reviews.length > 0) ? 0 : 1);
			frm.set_df_property("writer_copilot_feedback", "hidden", 1);
			frm.set_df_property("ai_reviews", "hidden", (reviewer_reviews.length > 0) ? 0 : 1);

			if (reviewer_reviews.length > 0) {
				frm.set_value("ai_score", reviewer_reviews[reviewer_reviews.length - 1].score);
			}
		} else if (!is_lead) {
			// Writer sees ONLY Writer feedback & Writer reviews; STRICTLY HIDE Reviewer feedback & instructions
			frm.set_df_property("writer_copilot_feedback", "hidden", (frm.doc.writer_copilot_feedback || writer_reviews.length > 0) ? 0 : 1);
			frm.set_df_property("reviewer_copilot_feedback", "hidden", 1);
			frm.set_df_property("ai_reviews", "hidden", (writer_reviews.length > 0) ? 0 : 1);

			if (writer_reviews.length > 0) {
				frm.set_value("ai_score", writer_reviews[writer_reviews.length - 1].score);
			}
		} else if (is_lead) {
			// Lead sees BOTH Writer and Reviewer feedback
			frm.set_df_property("writer_copilot_feedback", "hidden", (frm.doc.writer_copilot_feedback) ? 0 : 1);
			frm.set_df_property("reviewer_copilot_feedback", "hidden", (frm.doc.reviewer_copilot_feedback) ? 0 : 1);
			frm.set_df_property("ai_reviews", "hidden", (frm.doc.ai_reviews && frm.doc.ai_reviews.length > 0) ? 0 : 1);
		}

		// Filter child grid rows rendered on the form so Writer sees Writer rows and Reviewer sees Reviewer rows
		if (frm.fields_dict.ai_reviews && frm.fields_dict.ai_reviews.grid) {
			const grid = frm.fields_dict.ai_reviews.grid;
			grid.grid_rows.forEach(row => {
				if (!is_lead) {
					if (is_doc_reviewer && row.doc.review_type !== "Reviewer") {
						row.wrapper.hide();
					} else if (!is_doc_reviewer && row.doc.review_type !== "Writer") {
						row.wrapper.hide();
					} else {
						row.wrapper.show();
					}
				} else {
					row.wrapper.show();
				}
			});
		}

		frm.refresh_field("ai_score");
		frm.refresh_field("ai_review_status");
		frm.refresh_field("writer_copilot_feedback");
		frm.refresh_field("reviewer_copilot_feedback");
		frm.refresh_field("ai_reviews");
	},

	validate(frm) {
		const desc_val = frm.doc.description || frm.doc.topic;
		if (desc_val && String(desc_val).trim().length > 500) {
			const current_len = String(desc_val).trim().length;
			frappe.msgprint(__("<b>Description</b> exceeds maximum limit of 500 characters. (Current length: {0} characters)", [current_len]));
			frappe.validated = false;
		}
	},

	description(frm) {
		frm.trigger("update_description_inline_counter");
	},

	topic(frm) {
		frm.trigger("update_description_inline_counter");
	},

	update_description_inline_counter(frm) {
		const desc_val = frm.doc.description || frm.doc.topic;
		const len = desc_val ? String(desc_val).trim().length : 0;
		const target_field = frm.doc.description !== undefined ? "description" : "topic";
		if (len > 500) {
			frm.set_df_property(target_field, "description", `<b style="color: #dc2626; font-weight: 600;">Description exceeds 500 characters limit (${len}/500)</b>`);
		} else if (len > 0) {
			frm.set_df_property(target_field, "description", `<span style="color: #6b7280;">Character count: ${len}/500</span>`);
		} else {
			frm.set_df_property(target_field, "description", "Maximum 500 characters allowed");
		}
	},

	filter_workflow_actions(frm) {
		const current_user = (frappe.session.user || "").toLowerCase();
		const doc_assigned = (frm.doc.assigned_to || "").toLowerCase();
		const doc_reviewer = (frm.doc.reviewer_technical || "").toLowerCase();

		const is_doc_writer = (current_user === doc_assigned);
		const is_doc_reviewer = (current_user === doc_reviewer);
		const is_global_lead = frappe.user.has_role("Marketing Lead") || frappe.user.has_role("System Manager") || frappe.session.user === "Administrator";
		const is_lead = is_global_lead && !is_doc_writer;

		const applyFilter = () => {
			if (!frm.page || !frm.page.wrapper) return;

			const hideAction = (label) => {
				const selector = [
					`.actions-btn-group .dropdown-menu li`,
					`.actions-btn-group .dropdown-menu .dropdown-item`,
					`.standard-actions .dropdown-menu li`,
					`.standard-actions .dropdown-menu .dropdown-item`,
					`.page-actions .dropdown-menu li`,
					`.page-actions .dropdown-menu .dropdown-item`,
					`[data-label='${label}']`
				].join(", ");

				frm.page.wrapper.find(selector).filter(function() {
					const t = $(this).text().trim();
					const dl = $(this).attr("data-label") || $(this).attr("data-action");
					return t === label || t.startsWith(label) || dl === label;
				}).hide();

				frm.page.wrapper.find(`button, a.btn`).filter(function() {
					const t = $(this).text().trim();
					const dl = $(this).attr("data-label") || $(this).attr("data-action");
					return (t === label || dl === label) && !$(this).hasClass("btn-primary-action");
				}).hide();
			};

			if (is_doc_writer) {
				// The assigned writer must NEVER see reviewer actions or publishing actions on their own deliverable
				hideAction(__("Request Changes"));
				hideAction("Request Changes");
				hideAction(__("Approve"));
				hideAction("Approve");
				hideAction(__("Publish"));
				hideAction("Publish");
			} else if (is_doc_reviewer && !is_lead) {
				// The assigned reviewer must NEVER see writer drafting actions or publishing actions
				hideAction(__("Start Work"));
				hideAction("Start Work");
				hideAction(__("Submit for Review"));
				hideAction("Submit for Review");
				hideAction(__("Resubmit Draft"));
				hideAction("Resubmit Draft");
				hideAction(__("Publish"));
				hideAction("Publish");
			}
		};

		applyFilter();
		setTimeout(applyFilter, 50);
		setTimeout(applyFilter, 150);
		setTimeout(applyFilter, 350);
		setTimeout(applyFilter, 700);
	}
});