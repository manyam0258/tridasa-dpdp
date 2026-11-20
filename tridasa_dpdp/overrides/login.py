"""Send employees with pending mandatory training straight to it after login."""

import frappe
from frappe.utils import getdate

from tridasa_dpdp.utils import OPEN_STATUSES

FAR_FUTURE = getdate("2999-12-31")


def redirect_to_pending_training(login_manager):
	try:
		user = login_manager.user
		if user in ("Administrator", "Guest"):
			return
		from tridasa_dpdp.services.enrolment import link_user_assignments

		link_user_assignments(user)  # their Employee may have been linked to this login after assignment
		if frappe.form_dict.get("redirect_to"):
			return  # they followed a specific link; respect it
		target = get_pending_training(user)
		if target:
			frappe.cache.hset("redirect_after_login", user, f"/training/course?a={target}")
	except Exception:
		frappe.log_error(title="Tridasa DPDP: login redirect failed")  # never block a login


def get_pending_training(user: str) -> str | None:
	"""The most urgent open assignment (overdue first, then earliest due) whose course redirects on login."""
	rows = frappe.get_all(
		"Training Assignment",
		filters={"user": user, "status": ("in", OPEN_STATUSES)},
		fields=["name", "course", "overdue", "due_date"],
	)
	rows = [
		r
		for r in rows
		if frappe.get_cached_value("Training Course", r.course, "redirect_on_login")
		and frappe.get_cached_value("Training Course", r.course, "status") == "Published"
	]
	if not rows:
		return None
	rows.sort(key=lambda r: (not r.overdue, getdate(r.due_date) if r.due_date else FAR_FUTURE))
	return rows[0].name
