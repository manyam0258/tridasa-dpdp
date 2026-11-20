"""Inviting employees to a course and keeping them moving: invites, reminders,
manager escalation and re-certification."""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, format_date, getdate, now_datetime, today

from tridasa_dpdp.utils import LEARNER_ROLE, OPEN_STATUSES, course_url, get_url, safe_sendmail

EMPLOYEE_FIELDS = [
	"name",
	"employee_name",
	"first_name",
	"last_name",
	"status",
	"company",
	"user_id",
	"prefered_email",
	"company_email",
	"personal_email",
	"reports_to",
]


# ---------------------------------------------------------------- invites


def invite_employees(course: str, employees: list[str], due_in_days: int | None = None, notify: bool = True) -> dict:
	"""Assign many employees. With notify=False nobody is emailed and no logins are created."""
	course_doc = frappe.get_doc("Training Course", course)
	if course_doc.status != "Published":
		frappe.throw(_("Publish the course before inviting employees."))

	summary = {"invited": 0, "reinvited": 0, "already_enrolled": 0, "skipped": 0, "users_created": 0, "emails_failed": 0, "no_email": []}
	for employee in employees:
		result = invite_employee(course_doc, employee, due_in_days, notify=notify)
		if result["action"] == "no_email":
			summary["no_email"].append(employee)
		else:
			summary[result["action"]] += 1
		summary["users_created"] += int(bool(result.get("user_created")))
		summary["emails_failed"] += int(result.get("emailed") is False)
	return summary


def invite_employee(
	course_doc, employee: str, due_in_days: int | None = None, kind: str = "invite", notify: bool = True
) -> dict:
	"""Assign one employee. notify=True also creates a login if needed and emails them;
	notify=False only creates the assignment, linked to whatever login they already have."""
	emp = frappe.db.get_value("Employee", employee, EMPLOYEE_FIELDS, as_dict=True)
	if not emp or emp.status != "Active":
		return {"action": "skipped"}

	existing = frappe.db.get_value(
		"Training Assignment", {"course": course_doc.name, "employee": employee}, ["name", "status"], as_dict=True
	)
	if existing and existing.status not in ("Expired", "Cancelled"):
		return {"action": "already_enrolled", "assignment": existing.name}

	user_created, password_link = False, None
	if notify:
		user, user_created, password_link = ensure_user(emp)
		if not user:
			return {"action": "no_email"}
	else:
		user = linked_user(emp)

	due = add_days(today(), due_in_days if due_in_days is not None else (course_doc.due_in_days or 14))
	if existing:
		assignment = frappe.get_doc("Training Assignment", existing.name)
		assignment.reset_for_new_cycle(due)
		action = "reinvited"
	else:
		assignment = frappe.get_doc(
			{
				"doctype": "Training Assignment",
				"course": course_doc.name,
				"employee": employee,
				"due_date": due,
			}
		)
		action = "invited"

	assignment.user = user
	assignment.email = (frappe.db.get_value("User", user, "email") if user else None) or employee_email(emp)
	assignment.invited_on = now_datetime()
	assignment.flags.ignore_permissions = True
	if assignment.is_new():
		assignment.insert()
	else:
		assignment.save()

	result = {"action": action, "assignment": assignment.name, "user_created": user_created}
	if notify:
		result["emailed"] = send_assignment_email(
			assignment, kind="recert" if existing else kind, password_link=password_link
		)
		if result["emailed"]:
			assignment.db_set("invitation_emailed_on", now_datetime(), update_modified=False)
	return result


def employee_email(emp) -> str | None:
	return (emp.prefered_email or emp.company_email or emp.personal_email or "").strip().lower() or None


def linked_user(emp) -> str | None:
	"""The employee's existing, enabled login, if any. Never creates one."""
	if emp.user_id and frappe.db.get_value("User", emp.user_id, "enabled"):
		return emp.user_id
	return None


def link_user_assignments(user: str) -> int:
	"""Attach assignments to a login that was linked to the Employee after they were
	assigned (e.g. a test user linked later). Returns how many were updated."""
	if not user or user in ("Guest", "Administrator"):
		return 0
	employees = frappe.get_all("Employee", filters={"user_id": user}, pluck="name")
	if not employees:
		return 0
	email = frappe.db.get_value("User", user, "email")
	updated = 0
	for r in frappe.get_all(
		"Training Assignment",
		filters={"employee": ("in", employees), "status": ("!=", "Cancelled")},
		fields=["name", "user"],
	):
		if r.user != user:
			frappe.db.set_value("Training Assignment", r.name, {"user": user, "email": email}, update_modified=False)
			updated += 1
	return updated


def email_invitations(course: str, scope: str = "not_emailed", department: str | None = None) -> dict:
	"""HR-triggered: email everyone assigned to the course who hasn't finished it.
	scope='not_emailed' skips anyone already sent an invitation; scope='open' emails all.
	Creates portal logins (with set-password links) for employees who have none."""
	filters = {"course": course, "status": ("in", OPEN_STATUSES)}
	if scope == "not_emailed":
		filters["invitation_emailed_on"] = ("is", "not set")
	if department:
		filters["department"] = department

	summary = {"emailed": 0, "emails_failed": 0, "users_created": 0, "no_email": []}
	names = frappe.get_all("Training Assignment", filters=filters, pluck="name", order_by="employee_name asc")
	for i, name in enumerate(names):
		assignment = frappe.get_doc("Training Assignment", name)
		emp = frappe.db.get_value("Employee", assignment.employee, EMPLOYEE_FIELDS, as_dict=True)
		user, created, password_link = ensure_user(emp)
		if not user:
			summary["no_email"].append(assignment.employee)
			continue
		summary["users_created"] += int(created)
		if assignment.user != user:
			assignment.db_set({"user": user, "email": frappe.db.get_value("User", user, "email")}, update_modified=False)

		first_time = not assignment.invitation_emailed_on
		kind = "invite" if first_time else ("overdue" if assignment.overdue else "reminder")
		if send_assignment_email(assignment, kind=kind, password_link=password_link):
			if first_time:
				values = {"invitation_emailed_on": now_datetime()}
			else:
				values = {"reminders_sent": (assignment.reminders_sent or 0) + 1, "last_reminder_on": now_datetime()}
			assignment.db_set(values, update_modified=False)
			summary["emailed"] += 1
		else:
			summary["emails_failed"] += 1
		if i % 50 == 49:
			frappe.db.commit()  # long runs: keep progress
	return summary


def ensure_user(emp) -> tuple[str | None, bool, str | None]:
	"""Return (user, created, set-password link). Creates a portal-only login for
	employees who have none, and links it to the Employee record."""
	if emp.user_id and frappe.db.get_value("User", emp.user_id, "enabled"):
		_add_learner_role(emp.user_id)
		return emp.user_id, False, None

	email = (emp.prefered_email or emp.company_email or emp.personal_email or "").strip().lower()
	if not email:
		return None, False, None

	created = False
	if frappe.db.exists("User", email):
		user = email
		if not frappe.db.get_value("User", user, "enabled"):
			return None, False, None
	else:
		user_doc = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": emp.first_name or emp.employee_name,
				"last_name": emp.last_name,
				"user_type": "Website User",
				"send_welcome_email": 0,
				"roles": [{"role": LEARNER_ROLE}],
			}
		)
		user_doc.flags.ignore_permissions = True
		user_doc.insert()
		user, created = user_doc.name, True

	_add_learner_role(user)
	# Link without re-saving the whole Employee (avoids unrelated HR validations)
	if not frappe.db.exists("Employee", {"user_id": user, "name": ("!=", emp.name)}):
		frappe.db.set_value("Employee", emp.name, "user_id", user)

	password_link = None
	if created or not frappe.db.get_value("User", user, "last_login"):
		password_link = make_password_link(user)
	return user, created, password_link


def make_password_link(user: str) -> str:
	"""Set-password link for someone who has never logged in. After setting a
	password they land on their trainings instead of the default home page."""
	frappe.cache.hset("redirect_after_login", user, "/training")
	return frappe.get_doc("User", user)._reset_password(send_email=False)


def _add_learner_role(user: str):
	if not frappe.db.exists("Has Role", {"parent": user, "parenttype": "User", "role": LEARNER_ROLE}):
		user_doc = frappe.get_doc("User", user)
		user_doc.flags.ignore_permissions = True
		user_doc.add_roles(LEARNER_ROLE)


# ---------------------------------------------------------------- emails

SUBJECTS = {
	"invite": "Action needed: complete {course} by {due}",
	"reminder": "Reminder: {course} is due on {due}",
	"overdue": "Overdue: please complete {course} today",
	"recert": "Time to re-certify: {course} (due {due})",
}


def send_assignment_email(assignment, kind: str = "invite", password_link: str | None = None) -> bool:
	if not assignment.email:
		return False
	course = frappe.get_cached_doc("Training Course", assignment.course)
	due = format_date(assignment.due_date, "d MMMM yyyy") if assignment.due_date else ""
	if kind != "invite" and not password_link and not frappe.db.get_value("User", assignment.user, "last_login"):
		# They never logged in: every nudge should carry a fresh set-password link
		password_link = make_password_link(assignment.user)

	return safe_sendmail(
		recipients=[assignment.email],
		subject=SUBJECTS[kind].format(course=course.course_name, due=due),
		template="training_invite",
		args={
			"kind": kind,
			"employee_name": assignment.employee_name,
			"course": course,
			"due_date": due,
			"slides": len(course.chapters),
			"minutes": sum((c.estimated_minutes or 0) for c in course.chapters),
			"start_url": course_url(assignment.name),
			"password_link": password_link,
			"portal_url": get_url("/training"),
			"progress": assignment.progress or 0,
			"status": assignment.status,
		},
		reference_doctype="Training Assignment",
		reference_name=assignment.name,
		now=frappe.flags.in_test,
	)


def send_manager_escalation(assignment) -> bool:
	if not assignment.reports_to:
		return False
	manager = frappe.db.get_value(
		"Employee", assignment.reports_to, ["employee_name", "user_id", "prefered_email", "company_email"], as_dict=True
	)
	email = manager and (manager.user_id or manager.prefered_email or manager.company_email)
	if not email:
		return False
	course = frappe.get_cached_doc("Training Course", assignment.course)
	return safe_sendmail(
		recipients=[email],
		cc=[assignment.email] if assignment.email else None,
		subject=_("Overdue mandatory training: {0} – {1}").format(assignment.employee_name, course.course_name),
		template="training_escalation",
		args={
			"manager_name": manager.employee_name,
			"employee_name": assignment.employee_name,
			"course_name": course.course_name,
			"due_date": format_date(assignment.due_date, "d MMMM yyyy"),
			"status": assignment.status,
			"progress": assignment.progress or 0,
		},
		reference_doctype="Training Assignment",
		reference_name=assignment.name,
	)


# ---------------------------------------------------------------- scheduled


def send_due_reminders(course: str | None = None, force: bool = False) -> int:
	"""Nudge every open assignment whose last nudge is older than the course interval."""
	filters = {"status": "Published"}
	if course:
		filters["name"] = course
	sent = 0
	for c in frappe.get_all("Training Course", filters=filters, fields=["name", "reminder_every_days"]):
		if not (force or c.reminder_every_days):
			continue
		for a in frappe.get_all(
			"Training Assignment",
			filters={"course": c.name, "status": ("in", OPEN_STATUSES), "invitation_emailed_on": ("is", "set")},
			fields=["name", "invitation_emailed_on", "last_reminder_on"],
		):
			last = a.last_reminder_on or a.invitation_emailed_on
			if not force and last and date_diff(today(), getdate(last)) < c.reminder_every_days:
				continue
			doc = frappe.get_doc("Training Assignment", a.name)
			if not doc.can_still_finish():
				continue
			if not send_assignment_email(doc, kind="overdue" if doc.overdue else "reminder"):
				continue
			frappe.db.set_value(
				"Training Assignment",
				a.name,
				{"reminders_sent": (doc.reminders_sent or 0) + 1, "last_reminder_on": now_datetime()},
				update_modified=False,
			)
			sent += 1
	return sent


def mark_overdue_and_escalate():
	for a in frappe.get_all(
		"Training Assignment",
		filters={"status": ("in", OPEN_STATUSES), "due_date": ("<", today())},
		fields=["name", "overdue", "escalated_on", "course", "invitation_emailed_on"],
	):
		if not a.overdue:
			frappe.db.set_value("Training Assignment", a.name, "overdue", 1, update_modified=False)
		if a.escalated_on or not frappe.get_cached_value("Training Course", a.course, "escalate_to_manager"):
			continue
		if not a.invitation_emailed_on:
			continue  # never told about it: don't escalate to their manager
		if send_manager_escalation(frappe.get_doc("Training Assignment", a.name)):
			frappe.db.set_value("Training Assignment", a.name, "escalated_on", now_datetime(), update_modified=False)


def expire_certificates():
	"""Expire lapsed certificates and re-invite the holder for the next cycle."""
	for cert in frappe.get_all(
		"Training Certificate",
		filters={"status": "Active", "valid_until": ("<", today())},
		fields=["name", "assignment", "course", "employee"],
	):
		frappe.db.set_value("Training Certificate", cert.name, "status", "Expired")
		if cert.assignment:
			frappe.db.set_value("Training Assignment", cert.assignment, "status", "Expired")
		course = frappe.get_doc("Training Course", cert.course)
		if course.status == "Published":
			invite_employee(course, cert.employee, kind="recert")


def get_matching_employees(company=None, department=None, branch=None, designation=None, employees=None) -> list[str]:
	filters = {"status": "Active"}
	for field, value in (("company", company), ("department", department), ("branch", branch), ("designation", designation)):
		if value:
			filters[field] = value
	if employees:
		filters["name"] = ("in", employees)
	return frappe.get_all("Employee", filters=filters, pluck="name", order_by="employee_name asc")


# ---------------------------------------------------------------- assign to everyone


def assign_all_active(course: str | None = None) -> dict:
	"""Silently assign every active employee who has no assignment yet in each course set
	to 'Assign to All Active Employees' (no emails, no new logins). Employees HR
	cancelled are left alone. HR sends invitation emails separately, when they choose."""
	filters = {"status": "Published", "assign_to_all_active": 1}
	if course:
		filters["name"] = course
	results = {}
	for c in frappe.get_all("Training Course", filters=filters, fields=["name", "company"]):
		enrolled = set(frappe.get_all("Training Assignment", filters={"course": c.name}, pluck="employee"))
		pending = [e for e in get_matching_employees(company=c.company) if e not in enrolled]
		if pending:
			results[c.name] = invite_employees(c.name, pending, notify=False)
			frappe.db.commit()  # long runs: keep progress if a later invite fails
	return results


def enqueue_assign_all(course: str | None = None):
	"""Background, de-duplicated. Used on publish and after every migrate (i.e. each deploy)."""
	if frappe.flags.in_test:
		return
	try:
		frappe.enqueue(
			"tridasa_dpdp.services.enrolment.assign_all_active",
			queue="long",
			timeout=3600,
			course=course,
			job_id=f"tridasa_dpdp:assign_all:{course or 'all'}",
			deduplicate=True,
			enqueue_after_commit=True,
		)
	except Exception:
		# Never fail an install/migrate over this; the daily job will catch up
		frappe.log_error(title="Tridasa DPDP: could not queue assign-all job")


def after_migrate():
	enqueue_assign_all()
