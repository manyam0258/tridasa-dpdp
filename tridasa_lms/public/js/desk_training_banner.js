// Desk users with pending mandatory training see a reminder once per session.
$(document).on("app_ready", () => {
	const KEY = "tridasa_lms_banner_shown";
	try {
		if (sessionStorage.getItem(KEY)) return;
		sessionStorage.setItem(KEY, "1");
	} catch (e) {
		/* storage blocked: show anyway */
	}
	frappe.call({ method: "tridasa_lms.api.get_pending_for_session", type: "GET" }).then(({ message }) => {
		if (!message || !message.length) return;
		const t = message[0];
		const more = message.length > 1 ? __(" (+{0} more)", [message.length - 1]) : "";
		const due = t.due_date ? __("due {0}", [frappe.datetime.str_to_user(t.due_date)]) : "";
		frappe.show_alert(
			{
				message: `${t.overdue ? __("Overdue") : __("Mandatory training")}: <b>${frappe.utils.escape_html(
					t.course
				)}</b> ${due}${more} · <a href="/training/course?a=${encodeURIComponent(t.name)}">${__("Start now")}</a>`,
				indicator: t.overdue ? "red" : "orange",
			},
			20
		);
	});
});
