"""Keep training enrolment in step with the employee lifecycle."""

import frappe
from frappe import _
from frappe.utils import now_datetime

from tridasa_dpdp.utils import OPEN_STATUSES


def enroll_new_joiner(doc, method=None):
	if doc.status != "Active":
		return
	for name in frappe.get_all(
		"Training Course", filters={"status": "Published", "auto_enroll_new_joiners": 1}, pluck="name"
	):
		frappe.enqueue(
			"tridasa_dpdp.overrides.employee._invite",
			course=name,
			employee=doc.name,
			enqueue_after_commit=True,
		)


def _invite(course, employee):
	from tridasa_dpdp.services.enrolment import invite_employee

	invite_employee(frappe.get_doc("Training Course", course), employee)


def on_status_change(doc, method=None):
	"""Employees who leave drop out of the pending numbers."""
	if not doc.has_value_changed("status") or doc.status == "Active":
		return
	for name in frappe.get_all(
		"Training Assignment", filters={"employee": doc.name, "status": ("in", OPEN_STATUSES)}, pluck="name"
	):
		frappe.db.set_value(
			"Training Assignment",
			name,
			{"status": "Cancelled", "overdue": 0, "cancel_reason": _("Employee status changed to {0} on {1}").format(doc.status, now_datetime().date())},
		)
