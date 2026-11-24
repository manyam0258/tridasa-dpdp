"""Keep training enrolment in step with the employee lifecycle.

Assignment happens inline (no background worker needed) and silently: no email, no new login."""

import frappe
from frappe import _
from frappe.utils import now_datetime

from tridasa_dpdp.utils import OPEN_STATUSES


def enroll_new_joiner(doc, method=None):
	if doc.status == "Active":
		_assign(doc.name, include_new_joiner_courses=True)


def on_status_change(doc, method=None):
	"""Employees who leave drop out of the pending numbers; re-activated ones are assigned
	again. A login linked to the employee later picks up their assignments."""
	if doc.user_id and doc.has_value_changed("user_id"):
		from tridasa_dpdp.services.enrolment import link_user_assignments

		link_user_assignments(doc.user_id)
		if doc.status == "Active":
			_assign(doc.name)  # e.g. a login added to an employee who was missed earlier
	if not doc.has_value_changed("status"):
		return
	if doc.status == "Active":
		_assign(doc.name, reopen_cancelled=True, include_new_joiner_courses=True)
		return
	for name in frappe.get_all(
		"Training Assignment", filters={"employee": doc.name, "status": ("in", OPEN_STATUSES)}, pluck="name"
	):
		frappe.db.set_value(
			"Training Assignment",
			name,
			{"status": "Cancelled", "overdue": 0, "cancel_reason": _("Employee status changed to {0} on {1}").format(doc.status, now_datetime().date())},
		)


def _assign(employee: str, **kwargs):
	"""Never let a training problem block anyone from saving an Employee."""
	from tridasa_dpdp.services.enrolment import assign_employee_now

	frappe.db.savepoint("tridasa_dpdp_assign")
	try:
		assign_employee_now(employee, **kwargs)
	except Exception:
		frappe.db.rollback(save_point="tridasa_dpdp_assign")
		frappe.log_error(title=f"Tridasa DPDP: could not assign training to {employee}")
