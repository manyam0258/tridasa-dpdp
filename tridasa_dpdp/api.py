"""Whitelisted endpoints.

Learners never get DocType permissions: every learner endpoint loads the
assignment and checks it belongs to the session user before acting.
"""

import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, format_date

from tridasa_dpdp.services import assessment, enrolment
from tridasa_dpdp.utils import MANAGER_ROLES, OPEN_STATUSES, attempts_left, is_training_manager

ASYNC_INVITE_THRESHOLD = 25


# ================================================================ learner


@frappe.whitelist()
def get_my_trainings() -> list[dict]:
	_require_login()
	enrolment.ensure_my_assignments(frappe.session.user)
	rows = frappe.get_all(
		"Training Assignment",
		filters={"user": frappe.session.user, "status": ("!=", "Cancelled")},
		fields=["name", "course", "status", "progress", "due_date", "overdue", "best_score", "certificate"],
		order_by="modified desc",
	)
	for r in rows:
		course = frappe.get_cached_doc("Training Course", r.course)
		r.course_name = course.course_name
		r.tagline = course.tagline
		r.due_label = format_date(r.due_date, "d MMM yyyy") if r.due_date else None
	return rows


@frappe.whitelist()
def get_course_player(assignment: str) -> dict:
	doc = _my_assignment(assignment)
	course = frappe.get_cached_doc("Training Course", doc.course)
	read = {r.chapter_idx for r in doc.chapter_progress}
	open_attempt = assessment.get_open_attempt(doc.name) if doc.status in OPEN_STATUSES else None
	if not open_attempt:
		doc.reload()  # get_open_attempt may have timed out an attempt and updated the assignment

	cert = None
	if doc.certificate:
		cert = frappe.db.get_value(
			"Training Certificate", doc.certificate, ["name", "issue_date", "valid_until", "status", "score"], as_dict=True
		)
		cert.issue_label = format_date(cert.issue_date, "d MMMM yyyy")
		cert.valid_label = format_date(cert.valid_until, "d MMMM yyyy") if cert.valid_until else None

	return {
		"assignment": {
			"name": doc.name,
			"status": doc.status,
			"employee_name": doc.employee_name,
			"employee": doc.employee,
			"department": doc.department,
			"progress": doc.progress,
			"chapters_read": doc.chapters_read,
			"due_date": doc.due_date,
			"due_label": format_date(doc.due_date, "d MMMM yyyy") if doc.due_date else None,
			"overdue": doc.overdue,
			"attempts_used": doc.attempts_used,
			"attempts_left": attempts_left(course, doc),
			"best_score": doc.best_score,
			"can_attempt": doc.status in ("Course Completed", "Assessment Failed") and attempts_left(course, doc) != 0,
		},
		"course": {
			"name": course.name,
			"course_name": course.course_name,
			"tagline": course.tagline,
			"version": course.version,
			"introduction": course.introduction,
			"questions": course.questions_per_attempt,
			"pass_percentage": course.pass_percentage,
			"time_limit": course.time_limit_minutes,
			"max_attempts": course.max_attempts,
			"minutes": sum((c.estimated_minutes or 0) for c in course.chapters),
		},
		"chapters": [
			{"idx": c.idx, "title": c.chapter_title, "content": c.content, "minutes": c.estimated_minutes, "read": c.idx in read}
			for c in course.chapters
		],
		"open_attempt": assessment.paper_for_learner(open_attempt) if open_attempt else None,
		"history": frappe.get_all(
			"Training Assessment Attempt",
			filters={"assignment": doc.name, "cycle": doc.cycle or 1, "status": ("!=", "In Progress")},
			fields=["attempt_no", "score", "result", "status", "submitted_on"],
			order_by="attempt_no asc",
		),
		"certificate": cert,
	}


@frappe.whitelist(methods=["POST"])
def mark_chapter_read(assignment: str, idx: int) -> dict:
	doc = _my_assignment(assignment)
	if doc.status not in ("Invited", "In Progress", "Course Completed", "Assessment Failed", "Certified"):
		frappe.throw(_("This training is closed."))
	doc.mark_chapter_read(cint(idx))
	return {"status": doc.status, "progress": doc.progress, "chapters_read": doc.chapters_read}


@frappe.whitelist(methods=["POST"])
def start_attempt(assignment: str) -> dict:
	doc = _my_assignment(assignment)
	attempt = assessment.start_attempt(doc)
	return assessment.paper_for_learner(attempt)


@frappe.whitelist(methods=["POST"])
def submit_attempt(attempt: str, answers: str | dict) -> dict:
	doc = frappe.get_doc("Training Assessment Attempt", attempt)
	_my_assignment(doc.assignment)
	if isinstance(answers, str):
		answers = json.loads(answers or "{}")
	return assessment.submit_attempt(doc, answers)


@frappe.whitelist()
def download_certificate(name: str):
	cert = frappe.get_doc("Training Certificate", name)
	if cert.user != frappe.session.user and not is_training_manager():
		raise frappe.PermissionError
	if cert.status == "Revoked":
		frappe.throw(_("This certificate has been revoked."))
	frappe.local.response.filename = f"{cert.name}.pdf"
	frappe.local.response.filecontent = frappe.get_print(
		"Training Certificate", cert.name, print_format="DPDP Certificate", as_pdf=True
	)
	frappe.local.response.type = "pdf"


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=20, seconds=60)
def verify_certificate(certificate_no: str) -> dict:
	"""Public lookup so anyone shown a certificate can check it. Returns only what is printed on it."""
	certificate_no = (certificate_no or "").strip().upper()
	row = frappe.db.get_value(
		"Training Certificate",
		certificate_no,
		["name", "employee_name", "department", "course_name", "issue_date", "valid_until", "status"],
		as_dict=True,
	)
	if not row:
		return {"found": False}
	return {
		"found": True,
		"certificate_no": row.name,
		"employee_name": row.employee_name,
		"department": (row.department or "").rsplit(" - ", 1)[0],  # drop company abbreviation
		"course_name": row.course_name,
		"issue_date": format_date(row.issue_date, "d MMMM yyyy"),
		"valid_until": format_date(row.valid_until, "d MMMM yyyy") if row.valid_until else None,
		"status": row.status,
	}


# ================================================================ admin


@frappe.whitelist(methods=["POST"])
def invite_employees(
	course: str,
	company: str | None = None,
	department: str | None = None,
	branch: str | None = None,
	designation: str | None = None,
	employees: str | list | None = None,
	due_in_days: int | None = None,
	send_email: int | bool = 1,
) -> dict:
	frappe.only_for(MANAGER_ROLES)
	notify = bool(cint(send_email))
	if isinstance(employees, str):
		employees = json.loads(employees) if employees else None
	targets = enrolment.get_matching_employees(company, department, branch, designation, employees)
	due = cint(due_in_days) if due_in_days not in (None, "") else None
	if not targets:
		return {"matched": 0}

	if len(targets) > ASYNC_INVITE_THRESHOLD:
		frappe.enqueue(
			"tridasa_dpdp.api._invite_in_background",
			queue="long",
			timeout=3600,
			course=course,
			employees=targets,
			due_in_days=due,
			requested_by=frappe.session.user,
			notify=notify,
			enqueue_after_commit=True,
		)
		return {"matched": len(targets), "queued": True}

	return {"matched": len(targets), "notified": notify, **enrolment.invite_employees(course, targets, due, notify=notify)}


def _invite_in_background(course, employees, due_in_days, requested_by, notify=True):
	summary = enrolment.invite_employees(course, employees, due_in_days, notify=notify)
	summary["notified"] = notify
	frappe.publish_realtime(
		"tridasa_dpdp_invites_done", {"course": course, **summary}, user=requested_by, after_commit=True
	)


@frappe.whitelist(methods=["POST"])
def assign_all_now(course: str) -> dict:
	"""Assign every active employee, and every login without an Employee record, not yet in
	this course. Silent (no emails). Runs right away unless the company is very large."""
	frappe.only_for(MANAGER_ROLES)
	if frappe.db.get_value("Training Course", course, "status") != "Published":
		frappe.throw(_("Publish the course first."))
	pending = _count_unassigned(course)
	if not pending:
		return {"pending": 0}
	if pending <= enrolment.INLINE_ASSIGN_LIMIT:
		summary = enrolment.assign_all_active(course, commit=False).get(course, {})
		return {"pending": pending, "queued": False, **summary}
	frappe.enqueue(
		"tridasa_dpdp.services.enrolment.assign_all_active",
		queue="long",
		timeout=3600,
		course=course,
		job_id=f"tridasa_dpdp:assign_all:{course}",
		deduplicate=True,
		enqueue_after_commit=True,
	)
	return {"pending": pending, "queued": True}


def _count_unassigned(course: str) -> int:
	doc = frappe.get_doc("Training Course", course)
	enrolled = set(frappe.get_all("Training Assignment", filters={"course": course}, pluck="employee"))
	employees = sum(1 for e in enrolment.get_matching_employees(company=doc.company) if e not in enrolled)
	return employees + (0 if doc.company else len(enrolment.unassigned_users(course)))


@frappe.whitelist()
def get_invitation_counts(course: str) -> dict:
	"""For the Email Invitations dialog."""
	frappe.only_for(MANAGER_ROLES)
	unassigned = _count_unassigned(course)
	base = {"course": course, "status": ("in", OPEN_STATUSES)}
	return {
		# employees not assigned yet are assigned first, so they count as 'not emailed'
		"not_emailed": frappe.db.count("Training Assignment", {**base, "invitation_emailed_on": ("is", "not set")}) + unassigned,
		"open": frappe.db.count("Training Assignment", base) + unassigned,
		"certified": frappe.db.count("Training Assignment", {"course": course, "status": "Certified"}),
		"email_ready": enrolment.outgoing_email_ready(),
	}


@frappe.whitelist(methods=["POST"])
def email_invitations(course: str, scope: str = "open", department: str | None = None, note: str | None = None) -> dict:
	"""HR emails every active employee who hasn't finished the course (or only those not
	emailed yet). Anyone not assigned yet is assigned first. Normal-sized runs happen right
	away and return a summary; very large ones go to the background."""
	frappe.only_for(MANAGER_ROLES)
	if scope not in ("not_emailed", "open"):
		frappe.throw(_("Unknown recipient group."))
	if frappe.db.get_value("Training Course", course, "status") != "Published":
		frappe.throw(_("Publish the course first."))
	if not enrolment.outgoing_email_ready():
		frappe.throw(
			_("No default outgoing Email Account is set up, so emails can't be sent. Set one up in {0} (tick 'Enable Outgoing' and 'Default Outgoing'), then try again.").format(
				'<a href="/app/email-account">Email Account</a>'
			),
			title=_("Email not set up"),
		)
	_assign_missing(course)
	targets = frappe.db.count("Training Assignment", {"course": course, "status": ("in", OPEN_STATUSES)})
	if targets <= enrolment.INLINE_ASSIGN_LIMIT:
		summary = enrolment.email_invitations(course, scope, department or None, note=note, commit=False)
		return {"queued": False, **summary}
	frappe.enqueue(
		"tridasa_dpdp.api._email_in_background",
		queue="long",
		timeout=3600,
		course=course,
		scope=scope,
		department=department or None,
		note=note,
		requested_by=frappe.session.user,
		job_id=f"tridasa_dpdp:email_invitations:{course}",
		deduplicate=True,
		enqueue_after_commit=True,
	)
	return {"queued": True}


def _assign_missing(course: str):
	"""Everyone should be on the list before HR emails 'all employees'."""
	enrolment.assign_all_active(course, commit=False)


def _email_in_background(course, scope, department, requested_by, note=None):
	summary = enrolment.email_invitations(course, scope, department, note=note)
	frappe.publish_realtime(
		"tridasa_dpdp_emails_done", {"course": course, **summary}, user=requested_by, after_commit=True
	)


@frappe.whitelist(methods=["POST"])
def send_reminders_now(course: str) -> dict:
	frappe.only_for(MANAGER_ROLES)
	return {"sent": enrolment.send_due_reminders(course=course, force=True)}


@frappe.whitelist()
def get_course_dashboard(course: str) -> dict:
	frappe.only_for((*MANAGER_ROLES, "HR Manager"))
	rows = frappe.get_all(
		"Training Assignment",
		filters={"course": course, "status": ("!=", "Cancelled")},
		fields=["status", "overdue", "attempts_used", "best_score", "department"],
	)
	invited = len(rows)
	certified = sum(1 for r in rows if r.status == "Certified")
	stats = {
		"invited": invited,
		"not_started": sum(1 for r in rows if r.status == "Invited"),
		"reading": sum(1 for r in rows if r.status == "In Progress"),
		"slides_done": sum(1 for r in rows if r.status not in ("Invited", "In Progress")),
		"attempted": sum(1 for r in rows if r.attempts_used),
		"failed": sum(1 for r in rows if r.status == "Assessment Failed"),
		"certified": certified,
		"expired": sum(1 for r in rows if r.status == "Expired"),
		"overdue": sum(1 for r in rows if r.overdue),
		"completion": round(certified * 100 / invited, 1) if invited else 0,
	}
	scored = [r.best_score for r in rows if r.attempts_used]
	stats["avg_best_score"] = round(sum(scored) / len(scored), 1) if scored else None
	return stats


@frappe.whitelist()
def preview_paper(course: str) -> list[dict]:
	"""A sample paper with the answer key, for HR to sanity-check the bank."""
	frappe.only_for(MANAGER_ROLES)
	paper = assessment.build_paper(frappe.get_doc("Training Course", course))
	return [
		{
			"topic": q["topic"],
			"question": q["question_text"],
			"options": json.loads(q["options_json"]),
			"correct": q["correct_option"],
		}
		for q in paper
	]


@frappe.whitelist()
def get_pending_for_session() -> list[dict]:
	"""Open trainings for the logged-in user (kept for older cached Desk scripts)."""
	return get_desk_training_status()["pending"]


@frappe.whitelist()
def get_desk_training_status() -> dict:
	"""Used by the Desk navbar button and banner. Assigns missing mandatory training first."""
	if frappe.session.user == "Guest":
		return {"total": 0, "pending": []}
	enrolment.ensure_my_assignments(frappe.session.user)
	rows = frappe.get_all(
		"Training Assignment",
		filters={"user": frappe.session.user, "status": ("!=", "Cancelled")},
		fields=["name", "course", "due_date", "overdue", "status"],
		order_by="overdue desc, due_date asc",
	)
	pending = [r for r in rows if r.status in OPEN_STATUSES]
	for r in pending:
		r.course_name = frappe.get_cached_value("Training Course", r.course, "course_name") or r.course
	return {"total": len(rows), "pending": pending}


# ================================================================ helpers


def _require_login():
	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Please log in."))


def _my_assignment(name: str):
	_require_login()
	doc = frappe.get_doc("Training Assignment", name)
	if doc.user != frappe.session.user and enrolment.link_user_assignments(frappe.session.user):
		doc.reload()  # their Employee was linked to this login after the assignment was made
	if doc.user != frappe.session.user:
		raise frappe.PermissionError(_("This training is assigned to someone else."))
	if doc.status == "Cancelled":
		frappe.throw(_("This training has been withdrawn by HR."))
	return doc
