// Desk: a permanent "DPDP Training" button in the navbar for everyone who has training,
// and a banner under the navbar while any of it is still pending.
$(document).on("app_ready", () => {
	if (!frappe.session.user || frappe.session.user === "Guest") return;

	frappe
		.call({ method: "tridasa_dpdp.api.get_desk_training_status", type: "GET" })
		.then(({ message }) => {
			if (!message || !message.total) return;
			add_navbar_button(message.pending);
			if (message.pending.length) show_banner(message.pending);
		});
});

const DISMISS_KEY = "tridasa_dpdp_banner_dismissed";

function start_url(row) {
	return `/training/course?a=${encodeURIComponent(row.name)}`;
}

function add_navbar_button(pending) {
	if ($(".tridasa-dpdp-nav").length) return;
	const count = pending.length;
	const badge = count
		? `<span class="badge badge-pill" style="background:var(--red-500);color:#fff;margin-left:4px">${count}</span>`
		: "";
	const title = count ? __("You have {0} pending mandatory training(s)", [count]) : __("My DPDP training");
	const $li = $(`
		<li class="nav-item tridasa-dpdp-nav">
			<a class="nav-link btn btn-sm ${count ? "btn-primary" : "btn-default"}" href="/training"
				title="${title}" style="margin-right:8px;padding:4px 10px;white-space:nowrap">
				<svg class="icon icon-sm" style="${count ? "stroke:#fff" : ""}"><use href="#icon-education"></use></svg>
				<span class="d-none d-md-inline">${__("DPDP Training")}</span>${badge}
			</a>
		</li>`);
	$("header.navbar .navbar-collapse > ul.navbar-nav").first().prepend($li);
}

function show_banner(pending) {
	try {
		if (sessionStorage.getItem(DISMISS_KEY)) return;
	} catch (e) {
		/* storage blocked: show it */
	}
	if ($(".tridasa-dpdp-banner").length) return;
	const t = pending[0];
	const due = t.due_date ? __("due {0}", [frappe.datetime.str_to_user(t.due_date)]) : "";
	const more = pending.length > 1 ? __(" (+{0} more)", [pending.length - 1]) : "";
	const action = t.status === "Invited" ? __("Start now") : __("Continue");
	const colour = t.overdue ? "red" : "orange";
	const $banner = $(`
		<div class="tridasa-dpdp-banner" role="status"
			style="background:var(--${colour}-100);color:var(--${colour}-800);border-bottom:1px solid var(--${colour}-300);font-size:var(--text-sm)">
			<div class="container d-flex align-items-center" style="gap:12px;padding-top:8px;padding-bottom:8px">
				<span style="flex:1">
					<b>${t.overdue ? __("Overdue") : __("Mandatory training")}:</b>
					${frappe.utils.escape_html(t.course_name || t.course)} ${due}${more}
				</span>
				<a class="btn btn-xs btn-primary" href="${start_url(t)}">${action}</a>
				<button class="btn btn-xs btn-link" data-dismiss aria-label="${__("Hide for now")}"
					style="color:inherit">${__("Hide for now")}</button>
			</div>
		</div>`);
	$banner.find("[data-dismiss]").on("click", () => {
		try {
			sessionStorage.setItem(DISMISS_KEY, "1");
		} catch (e) {
			/* ignore */
		}
		$banner.remove();
	});
	$(".sticky-top").first().append($banner);
}
