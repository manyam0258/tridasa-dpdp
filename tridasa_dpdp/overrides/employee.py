"""Keep training enrolment in step with the employee lifecycle."""

import frappe
from frappe import _
from frappe.utils import now_datetime

from tridasa_dpdp.utils import OPEN_STATUSES


def enroll_new_joiner(doc, method=None):
	if doc.status == "Active":
		_enqueue_invites(doc.name)


def _enqueue_invites(employee: str):
	courses = set(
		frappe.get_all("Training Course", filters={"status": "Published", "auto_enroll_new_joiners": 1}, pluck="name")
	) | set(frappe.get_all("Training Course", filters={"status": "Published", "assign_to_all_active": 1}, pluck="name"))
	for name in courses:
		frappe.enqueue(
			"tridasa_dpdp.overrides.employee._invite",
			course=name,
			employee=employee,
			enqueue_after_commit=True,
		)


def _invite(course, employee):
	from tridasa_dpdp.services.enrolment import invite_employee

	# Silent: HR sends invitation emails when they choose ("Email Invitations")
	invite_employee(frappe.get_doc("Training Course", course), employee, notify=False)


def on_status_change(doc, method=None):
	"""Employees who leave drop out of the pending numbers; re-activated ones are assigned
	again. A login linked to the employee later picks up their assignments."""
	if doc.user_id and doc.has_value_changed("user_id"):
		from tridasa_dpdp.services.enrolment import link_user_assignments

		link_user_assignments(doc.user_id)
	if not doc.has_value_changed("status"):
		return
	if doc.status == "Active":
		_enqueue_invites(doc.name)  # invite_employee re-opens their cancelled assignment
		return
	for name in frappe.get_all(
		"Training Assignment", filters={"employee": doc.name, "status": ("in", OPEN_STATUSES)}, pluck="name"
	):
		frappe.db.set_value(
			"Training Assignment",
			name,
			{"status": "Cancelled", "overdue": 0, "cancel_reason": _("Employee status changed to {0} on {1}").format(doc.status, now_datetime().date())},
		)
