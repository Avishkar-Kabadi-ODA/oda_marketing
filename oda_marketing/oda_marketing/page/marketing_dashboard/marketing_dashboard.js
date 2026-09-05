// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.pages["marketing-dashboard"].on_page_load = function(wrapper) {
	const is_lead = frappe.user.has_role("Marketing Lead") || frappe.user.has_role("System Manager") || frappe.session.user === "Administrator";

	if (!is_lead) {
		frappe.show_not_permitted(__("Access Restricted: The Marketing Operations Dashboard is only accessible by Marketing Leads and System Managers."));
		frappe.set_route("List", "Content Item");
		return;
	}

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Marketing Operations Dashboard"),
		single_column: true
	});

	page.dashboard = new MarketingOperationsDashboard(page);
};

class MarketingOperationsDashboard {
	constructor(page) {
		this.page = page;
		this.wrapper = $(page.body);
		this.charts = {};
		this.options_loaded = false;
		this.last_data = null;

		this.setup_header_actions();
		this.render_layout();
		this.bind_filter_events();
		this.fetch_data();

		$(window).off("resize.marketing_dashboard").on("resize.marketing_dashboard", frappe.utils.debounce(() => {
			if (this.last_data) {
				this.render_charts(this.last_data);
			}
		}, 200));
	}

	setup_header_actions() {
		this.page.set_secondary_action(__("Refresh"), () => {
			this.fetch_data();
		}, "octicon octicon-sync");

		this.page.set_primary_action(__("View Content Items"), () => {
			frappe.set_route("List", "Content Item");
		}, "octicon octicon-checklist");
	}

	render_layout() {
		const current_year = new Date().getFullYear();

		const months = [
			{ label: __("Full Year"), val: "0" },
			{ label: __("January (M01)"), val: "1" },
			{ label: __("February (M02)"), val: "2" },
			{ label: __("March (M03)"), val: "3" },
			{ label: __("April (M04)"), val: "4" },
			{ label: __("May (M05)"), val: "5" },
			{ label: __("June (M06)"), val: "6" },
			{ label: __("July (M07)"), val: "7" },
			{ label: __("August (M08)"), val: "8" },
			{ label: __("September (M09)"), val: "9" },
			{ label: __("October (M10)"), val: "10" },
			{ label: __("November (M11)"), val: "11" },
			{ label: __("December (M12)"), val: "12" }
		];

		const month_options_html = months.map(m => `<option value="${m.val}">${m.label}</option>`).join("");
		const year_options_html = `
			<option value="${current_year}">${current_year}</option>
			<option value="${current_year - 1}">${current_year - 1}</option>
			<option value="${current_year + 1}">${current_year + 1}</option>
			<option value="All">All Years</option>
		`;

		this.wrapper.html(`
			<div class="marketing-dashboard-wrapper">
				<!-- Streamlined Theme-Aware Filter Card -->
				<div class="dashboard-filter-card">
					<div class="dashboard-filter-header">
						<div class="filter-header-left">
							<div class="filter-header-icon">
								<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
							</div>
							<div>
								<div class="filter-header-title">Filter Controls</div>
								<div class="filter-header-subtitle">Slice deliverables across calendars, years, and formats</div>
							</div>
							<span class="active-filter-badge" id="active-filter-summary">All Records</span>
						</div>
						<div>
							<button class="btn btn-xs btn-default btn-reset" id="btn-reset-filters">
								<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -1px; margin-right: 3px;"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
								Reset Filters
							</button>
						</div>
					</div>

					<div class="filter-grid">
						<!-- 1. Content Calendar Filter -->
						<div class="filter-item">
							<label class="filter-label">
								<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
								Content Calendar
							</label>
							<select class="filter-select" id="filter-calendar">
								<option value="All">All Calendars</option>
							</select>
						</div>

						<!-- 2. Year Filter -->
						<div class="filter-item">
							<label class="filter-label">
								<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
								Year
							</label>
							<select class="filter-select" id="filter-year">
								${year_options_html}
							</select>
						</div>

						<!-- 3. Month / Period Filter -->
						<div class="filter-item">
							<label class="filter-label">
								<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
								Month / Period
							</label>
							<select class="filter-select" id="filter-month">
								${month_options_html}
							</select>
						</div>

						<!-- 4. Format Filter -->
						<div class="filter-item">
							<label class="filter-label">
								<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
								Format
							</label>
							<select class="filter-select" id="filter-format">
								<option value="All">All Formats</option>
							</select>
						</div>
					</div>
				</div>

				<!-- Premium 4-Card Summary KPI Grid (Theme Adaptive) -->
				<div class="kpi-grid">
					<!-- 1. Total Deliverables -->
					<div class="kpi-box kpi-total" data-state="">
						<div class="kpi-top-row">
							<span class="kpi-title">Total Deliverables</span>
							<div class="kpi-icon-badge kpi-badge-indigo">
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
							</div>
						</div>
						<div class="kpi-value" id="kpi-total">0</div>
						<div class="kpi-subtitle">
							<span class="kpi-dot dot-indigo"></span> In current scope
						</div>
					</div>

					<!-- 2. In Progress -->
					<div class="kpi-box kpi-in-progress" data-state="In Progress">
						<div class="kpi-top-row">
							<span class="kpi-title">In Progress</span>
							<div class="kpi-icon-badge kpi-badge-orange">
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
							</div>
						</div>
						<div class="kpi-value" id="kpi-in-progress">0</div>
						<div class="kpi-subtitle">
							<span class="kpi-dot dot-orange"></span> Active drafting & research
						</div>
					</div>

					<!-- 3. Approved for Publishing -->
					<div class="kpi-box kpi-approved" data-state="Approved">
						<div class="kpi-top-row">
							<span class="kpi-title">Approved</span>
							<div class="kpi-icon-badge kpi-badge-cyan">
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
							</div>
						</div>
						<div class="kpi-value" id="kpi-approved">0</div>
						<div class="kpi-subtitle">
							<span class="kpi-dot dot-cyan"></span> Ready for publishing
						</div>
					</div>

					<!-- 4. Published Live -->
					<div class="kpi-box kpi-published" data-state="Published">
						<div class="kpi-top-row">
							<span class="kpi-title">Published</span>
							<div class="kpi-icon-badge kpi-badge-emerald">
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
							</div>
						</div>
						<div class="kpi-value" id="kpi-published">0</div>
						<div class="kpi-subtitle">
							<span class="kpi-dot dot-emerald"></span> Live across channels
						</div>
					</div>
				</div>

				<!-- Responsive Visual Charts Grid (Theme Adaptive) -->
				<div class="charts-grid">
					<div class="chart-card">
						<div class="chart-card-header">
							<div class="chart-card-icon-wrap" style="background: rgba(79, 70, 229, 0.12); color: #4F46E5;">
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
							</div>
							<div>
								<div class="chart-card-title">Workflow Pipeline Funnel</div>
								<div class="chart-card-subtitle">Distribution of deliverables across lifecycle stages</div>
							</div>
						</div>
						<div id="chart-status-funnel" class="chart-container"></div>
						<div id="funnel-custom-legend" class="dashboard-custom-legend"></div>
					</div>

					<div class="chart-card">
						<div class="chart-card-header">
							<div class="chart-card-icon-wrap" style="background: rgba(99, 102, 241, 0.12); color: #6366F1;">
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
							</div>
							<div>
								<div class="chart-card-title">Monthly Publication Cadence</div>
								<div class="chart-card-subtitle">Planned deliverable output volume by month</div>
							</div>
						</div>
						<div id="chart-monthly-cadence" class="chart-container"></div>
					</div>

					<div class="chart-card">
						<div class="chart-card-header">
							<div class="chart-card-icon-wrap" style="background: rgba(139, 92, 246, 0.12); color: #8B5CF6;">
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
							</div>
							<div>
								<div class="chart-card-title">Content Format Distribution</div>
								<div class="chart-card-subtitle">Omnichannel mix of blogs, carousels, and polls</div>
							</div>
						</div>
						<div id="chart-format-mix" class="chart-container"></div>
					</div>

					<div class="chart-card">
						<div class="chart-card-header">
							<div class="chart-card-icon-wrap" style="background: rgba(14, 165, 233, 0.12); color: #0EA5E9;">
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
							</div>
							<div>
								<div class="chart-card-title">Industry Domain Breakdown</div>
								<div class="chart-card-subtitle">Deliverables across target practice areas</div>
							</div>
						</div>
						<div id="chart-domain-breakdown" class="chart-container"></div>
					</div>
				</div>
			</div>
		`);

		// KPI Card Click Navigation
		this.wrapper.find(".kpi-box").on("click", function() {
			const state = $(this).data("state");
			if (state) {
				frappe.set_route("List", "Content Item", { workflow_state: state });
			} else {
				frappe.set_route("List", "Content Item");
			}
		});
	}

	bind_filter_events() {
		const me = this;

		// Listen to changes on any filter select
		this.wrapper.find(".filter-select").on("change", function() {
			me.fetch_data();
		});

		// Reset filters button
		this.wrapper.find("#btn-reset-filters").on("click", function() {
			const current_year = new Date().getFullYear();
			me.wrapper.find("#filter-calendar").val("All");
			me.wrapper.find("#filter-year").val(String(current_year));
			me.wrapper.find("#filter-month").val("0");
			me.wrapper.find("#filter-format").val("All");
			me.fetch_data();
		});
	}

	fetch_data() {
		const me = this;
		const cal = this.wrapper.find("#filter-calendar").val() || "All";
		const year = this.wrapper.find("#filter-year").val() || String(new Date().getFullYear());
		const month = this.wrapper.find("#filter-month").val() || "0";
		const format = this.wrapper.find("#filter-format").val() || "All";

		frappe.call({
			method: "oda_marketing.oda_marketing.doctype.content_item.content_item.get_dashboard_metrics",
			args: {
				calendar: cal,
				year: year,
				month: month,
				format: format
			},
			callback(res) {
				if (res && res.message) {
					const data = res.message;
					me.last_data = data;
					if (!me.options_loaded) {
						me.populate_dynamic_options(data);
						me.options_loaded = true;
					}
					me.render_kpis(data.kpis || {});
					me.render_charts(data);
					me.update_summary_label(cal, year, month, format);
				}
			}
		});
	}

	populate_dynamic_options(data) {
		// Populate Calendars
		if (data.calendars && data.calendars.length > 0) {
			const $cal = this.wrapper.find("#filter-calendar");
			const cur_val = $cal.val();
			$cal.empty().append(`<option value="All">All Calendars</option>`);
			data.calendars.forEach(c => {
				$cal.append(`<option value="${c.name}">${c.name}</option>`);
			});
			if (cur_val) $cal.val(cur_val);
		}

		// Populate Formats
		if (data.formats && data.formats.length > 0) {
			const $fmt = this.wrapper.find("#filter-format");
			const cur_val = $fmt.val();
			$fmt.empty().append(`<option value="All">All Formats</option>`);
			data.formats.forEach(f => {
				$fmt.append(`<option value="${f}">${f}</option>`);
			});
			if (cur_val) $fmt.val(cur_val);
		}
	}

	update_summary_label(cal, year, month, format) {
		let parts = [];
		if (cal !== "All") parts.push(cal);
		if (year !== "All") parts.push(year);
		if (month !== "0" && month !== "All") {
			const month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
			parts.push(month_names[parseInt(month)] || `M${month}`);
		}
		if (format !== "All") parts.push(format);

		const summary_text = parts.length > 0 ? parts.join(" • ") : "All Records";
		this.wrapper.find("#active-filter-summary").text(summary_text);
	}

	render_kpis(kpis) {
		this.wrapper.find("#kpi-total").text(kpis.total || 0);
		this.wrapper.find("#kpi-in-progress").text(kpis.in_progress || 0);
		this.wrapper.find("#kpi-approved").text(kpis.approved || 0);
		this.wrapper.find("#kpi-published").text(kpis.published || 0);
	}

	render_charts(data) {
		// 1. Status Funnel Donut Chart
		const status_color_map = {
			"Planned": "#64748B",
			"Briefed": "#2563EB",
			"In Progress": "#EA580C",
			"In Review": "#CA8A04",
			"In Revision": "#DC2626",
			"Approved": "#0891B2",
			"Published": "#059669"
		};

		const status_labels = Object.keys(data.status_distribution || {});
		const status_values = Object.values(data.status_distribution || {});
		const status_colors = status_labels.map(lbl => status_color_map[lbl] || "#6366F1");

		$("#chart-status-funnel").empty();
		this.charts.status_funnel = new frappe.Chart("#chart-status-funnel", {
			title: "",
			data: {
				labels: status_labels.length ? status_labels : ["None"],
				datasets: [{ name: __("Deliverables"), values: status_values.length ? status_values : [0] }]
			},
			type: "donut",
			height: 290,
			colors: status_colors,
			maxSlices: 8,
			truncateLegends: 0
		});

		// Responsive custom status pills below the donut chart
		const $legendContainer = $("#funnel-custom-legend");
		$legendContainer.empty();
		if (status_labels.length > 0) {
			const total_items = status_values.reduce((a, b) => a + b, 0);
			status_labels.forEach((label, idx) => {
				const val = status_values[idx] || 0;
				const color = status_colors[idx] || "#64748B";
				const pct = total_items > 0 ? Math.round((val / total_items) * 100) : 0;
				$legendContainer.append(`
					<div class="legend-pill" data-state="${label}" title="${label}: ${val} (${pct}%) • Click to filter">
						<span class="legend-dot" style="background-color: ${color};"></span>
						<span class="legend-name">${label}</span>
						<span class="legend-count">${val}</span>
					</div>
				`);
			});

			$legendContainer.find(".legend-pill").on("click", function() {
				const st = $(this).data("state");
				if (st) {
					frappe.set_route("List", "Content Item", { workflow_state: st });
				}
			});
		}

		// 2. Monthly Cadence Bar Chart
		const monthly_data = data.monthly_trend || [];
		const month_labels = monthly_data.map(m => m.month);
		const month_values = monthly_data.map(m => m.count);

		$("#chart-monthly-cadence").empty();
		this.charts.monthly_cadence = new frappe.Chart("#chart-monthly-cadence", {
			title: "",
			data: {
				labels: month_labels,
				datasets: [{ name: __("Deliverables"), values: month_values }]
			},
			type: "bar",
			height: 240,
			colors: ["#6366F1"]
		});

		// 3. Format Mix Bar Chart
		const format_labels = Object.keys(data.format_distribution || {});
		const format_values = Object.values(data.format_distribution || {});

		$("#chart-format-mix").empty();
		this.charts.format_mix = new frappe.Chart("#chart-format-mix", {
			title: "",
			data: {
				labels: format_labels.length ? format_labels : ["None"],
				datasets: [{ name: __("Deliverables"), values: format_values.length ? format_values : [0] }]
			},
			type: "bar",
			height: 240,
			colors: ["#8B5CF6"]
		});

		// 4. Industry Domain Breakdown Bar Chart
		const domain_labels = Object.keys(data.domain_distribution || {});
		const domain_values = Object.values(data.domain_distribution || {});

		$("#chart-domain-breakdown").empty();
		this.charts.domain_breakdown = new frappe.Chart("#chart-domain-breakdown", {
			title: "",
			data: {
				labels: domain_labels.length ? domain_labels : ["None"],
				datasets: [{ name: __("Deliverables"), values: domain_values.length ? domain_values : [0] }]
			},
			type: "bar",
			height: 240,
			colors: ["#0EA5E9"]
		});
	}
}
