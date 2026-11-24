"""Paper generation, grading and certificate issue. Correct answers never leave
the server until an attempt is submitted."""

import json
import random
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_months, add_to_date, flt, now_datetime, time_diff_in_seconds, today

from tridasa_dpdp.utils import attempts_left, safe_sendmail

GRACE_SECONDS = 60
_rng = random.SystemRandom()


def build_paper(course, exclude: set[str] | None = None) -> list[dict]:
	"""One question per topic (round-robin if the paper is longer than the topic
	list), preferring questions this employee has not seen before."""
	exclude = exclude or set()
	pools = defaultdict(list)
	for q in frappe.get_all(
		"Training Question", filters={"course": course.name, "enabled": 1}, fields=["name", "topic"]
	):
		pools[q.topic].append(q.name)
	if sum(len(p) for p in pools.values()) < course.questions_per_attempt:
		frappe.throw(_("The question bank for this course is too small. Please contact the IT department."))

	for pool in pools.values():
		_rng.shuffle(pool)
		pool.sort(key=lambda name: name in exclude)  # unseen first, stable within groups

	topics = list(pools)
	_rng.shuffle(topics)
	picks = []
	while len(picks) < course.questions_per_attempt:
		for topic in topics:
			if pools[topic] and len(picks) < course.questions_per_attempt:
				picks.append(pools[topic].pop(0))
	_rng.shuffle(picks)

	paper = []
	for name in picks:
		q = frappe.get_cached_doc("Training Question", name)
		options = [(o.option_text, o.is_correct) for o in q.options]
		_rng.shuffle(options)
		paper.append(
			{
				"question": q.name,
				"topic": q.topic,
				"question_text": q.question,
				"options_json": json.dumps([text for text, _ok in options]),
				"correct_option": next(i for i, (_text, ok) in enumerate(options) if ok),
				"explanation": q.explanation,
			}
		)
	return paper


def start_attempt(assignment) -> "frappe.model.document.Document":
	course = frappe.get_cached_doc("Training Course", assignment.course)
	in_progress = get_open_attempt(assignment.name)
	if in_progress:
		return in_progress

	if assignment.status in ("Certified", "Cancelled", "Expired"):
		frappe.throw(_("This assessment is not open for you."))
	if (assignment.chapters_read or 0) < len(course.chapters):
		frappe.throw(_("Finish all slides before starting the assessment."))
	if attempts_left(course, assignment) == 0:
		frappe.throw(_("You have used all your attempts. The IT department has been notified and can grant another attempt."))

	seen = set(
		frappe.get_all(
			"Training Attempt Question",
			filters={"parenttype": "Training Assessment Attempt", "parent": ("in", _attempt_names(assignment.name))},
			pluck="question",
		)
	)
	started = now_datetime()
	attempt = frappe.get_doc(
		{
			"doctype": "Training Assessment Attempt",
			"assignment": assignment.name,
			"course": course.name,
			"employee": assignment.employee,
			"employee_name": assignment.employee_name,
			"user": assignment.user,
			"cycle": assignment.cycle or 1,
			"attempt_no": (assignment.attempts_used or 0) + 1,
			"status": "In Progress",
			"started_on": started,
			"deadline": add_to_date(started, minutes=course.time_limit_minutes) if course.time_limit_minutes else None,
			"total_questions": course.questions_per_attempt,
			"questions": build_paper(course, seen),
		}
	)
	attempt.insert(ignore_permissions=True)

	# An attempt counts when it starts, so abandoning a paper can't be used to preview questions
	assignment.attempts_used = attempt.attempt_no
	assignment.last_attempt_on = started
	assignment.flags.ignore_permissions = True
	assignment.save()
	return attempt


def submit_attempt(attempt, answers: dict) -> dict:
	if attempt.status != "In Progress":
		frappe.throw(_("This attempt has already been submitted."))

	submitted = now_datetime()
	late = attempt.deadline and time_diff_in_seconds(submitted, attempt.deadline) > GRACE_SECONDS
	correct = 0
	for row in attempt.questions:
		selected = answers.get(str(row.idx), answers.get(row.idx))
		row.selected_option = int(selected) if selected not in (None, "") else -1
		row.is_correct = int(row.selected_option == row.correct_option)
		correct += row.is_correct

	course = frappe.get_cached_doc("Training Course", attempt.course)
	attempt.correct_answers = correct
	attempt.score = flt(correct * 100 / (len(attempt.questions) or 1), 1)
	attempt.submitted_on = submitted
	attempt.duration = int(time_diff_in_seconds(submitted, attempt.started_on))
	attempt.status = "Timed Out" if late else "Submitted"
	attempt.result = "Passed" if (not late and attempt.score >= flt(course.pass_percentage)) else "Failed"
	attempt.save(ignore_permissions=True)

	assignment = frappe.get_doc("Training Assignment", attempt.assignment)
	return _apply_result(assignment, attempt, course)


def time_out_attempt(attempt):
	"""Close an abandoned attempt after its deadline; it counts as a failed try."""
	attempt.status = "Timed Out"
	attempt.result = "Failed"
	attempt.correct_answers = 0
	attempt.score = 0
	attempt.submitted_on = now_datetime()
	attempt.duration = int(time_diff_in_seconds(attempt.submitted_on, attempt.started_on))
	attempt.save(ignore_permissions=True)
	assignment = frappe.get_doc("Training Assignment", attempt.assignment)
	_apply_result(assignment, attempt, frappe.get_cached_doc("Training Course", attempt.course))


def _apply_result(assignment, attempt, course) -> dict:
	assignment.last_score = attempt.score
	assignment.best_score = max(flt(assignment.best_score), attempt.score)
	certificate = None
	if attempt.result == "Passed":
		assignment.status = "Certified"
		assignment.certified_on = attempt.submitted_on
		assignment.overdue = 0
		if course.issue_certificate:
			certificate = issue_certificate(assignment, attempt, course)
			assignment.certificate = certificate.name
	elif assignment.status != "Certified":
		assignment.status = "Assessment Failed"
	assignment.flags.ignore_permissions = True
	assignment.save()

	if attempt.result == "Failed" and attempts_left(course, assignment) == 0:
		frappe.enqueue(
			"tridasa_dpdp.services.assessment.notify_attempts_exhausted",
			assignment=assignment.name,
			enqueue_after_commit=True,
		)

	return {
		"attempt": attempt.name,
		"status": attempt.status,
		"result": attempt.result,
		"score": attempt.score,
		"correct": attempt.correct_answers,
		"total": len(attempt.questions),
		"pass_percentage": course.pass_percentage,
		"attempts_left": attempts_left(course, assignment),
		"certificate": certificate.name if certificate else None,
		"review": get_review(attempt) if course.show_correct_answers else None,
	}


def get_review(attempt) -> list[dict]:
	return [
		{
			"idx": row.idx,
			"selected": row.selected_option,
			"correct": row.correct_option,
			"is_correct": row.is_correct,
			"explanation": row.explanation,
		}
		for row in attempt.questions
	]


def issue_certificate(assignment, attempt, course):
	months = course.certificate_validity_months
	cert = frappe.get_doc(
		{
			"doctype": "Training Certificate",
			"employee": assignment.employee,
			"employee_name": assignment.employee_name,
			"department": assignment.department,
			"designation": assignment.designation,
			"company": assignment.company,
			"user": assignment.user,
			"course": course.name,
			"course_name": course.course_name,
			"issue_date": today(),
			"valid_until": add_months(today(), months) if months else None,
			"score": attempt.score,
			"assignment": assignment.name,
			"attempt": attempt.name,
			"status": "Active",
		}
	)
	cert.insert(ignore_permissions=True)
	frappe.enqueue(
		"tridasa_dpdp.services.assessment.email_certificate",
		certificate=cert.name,
		enqueue_after_commit=True,
	)
	return cert


def email_certificate(certificate: str):
	cert = frappe.get_doc("Training Certificate", certificate)
	email = frappe.db.get_value("User", cert.user, "email") if cert.user else None
	if not email:
		return
	safe_sendmail(
		recipients=[email],
		subject=_("Your certificate: {0}").format(cert.course_name),
		template="training_certificate",
		args={"cert": cert, "portal_url": frappe.utils.get_url("/training")},
		attachments=[
			frappe.attach_print(
				"Training Certificate", cert.name, file_name=cert.name, print_format="DPDP Certificate"
			)
		],
		reference_doctype="Training Certificate",
		reference_name=cert.name,
	)


def notify_attempts_exhausted(assignment: str):
	doc = frappe.get_doc("Training Assignment", assignment)
	managers = [
		u
		for u in frappe.get_all(
			"Has Role", filters={"role": "Training Manager", "parenttype": "User"}, pluck="parent", distinct=True
		)
		if frappe.db.get_value("User", u, "enabled")
	]
	if not managers:
		return
	safe_sendmail(
		recipients=managers,
		subject=_("{0} has used all assessment attempts for {1}").format(doc.employee_name, doc.course),
		message=_(
			"<p>{0} ({1}) has not passed {2} after {3} attempt(s). Best score: {4}%.</p>"
			"<p>Open the assignment to grant another attempt: {5}</p>"
		).format(
			frappe.utils.escape_html(doc.employee_name),
			doc.employee,
			doc.course,
			doc.attempts_used,
			doc.best_score or 0,
			frappe.utils.get_url_to_form("Training Assignment", doc.name),
		),
		reference_doctype="Training Assignment",
		reference_name=doc.name,
	)


def get_open_attempt(assignment: str):
	name = frappe.db.get_value(
		"Training Assessment Attempt", {"assignment": assignment, "status": "In Progress"}, "name"
	)
	if not name:
		return None
	attempt = frappe.get_doc("Training Assessment Attempt", name)
	if attempt.deadline and time_diff_in_seconds(now_datetime(), attempt.deadline) > GRACE_SECONDS:
		time_out_attempt(attempt)
		return None
	return attempt


def paper_for_learner(attempt) -> dict:
	"""The paper without answers."""
	return {
		"attempt": attempt.name,
		"attempt_no": attempt.attempt_no,
		"deadline": str(attempt.deadline) if attempt.deadline else None,
		"seconds_left": int(time_diff_in_seconds(attempt.deadline, now_datetime())) if attempt.deadline else None,
		"questions": [
			{"idx": r.idx, "topic": r.topic, "question": r.question_text, "options": json.loads(r.options_json)}
			for r in attempt.questions
		],
	}


def close_stale_attempts():
	"""Hourly: time out attempts abandoned past their deadline."""
	cutoff = add_to_date(now_datetime(), seconds=-GRACE_SECONDS)
	for name in frappe.get_all(
		"Training Assessment Attempt",
		filters={"status": "In Progress", "deadline": ("<", cutoff)},
		pluck="name",
	):
		time_out_attempt(frappe.get_doc("Training Assessment Attempt", name))


def _attempt_names(assignment: str) -> list[str]:
	return frappe.get_all("Training Assessment Attempt", filters={"assignment": assignment}, pluck="name") or [""]
