import base64
import os

import frappe
from frappe.utils import get_url

TRAINING_ROUTE = "/training"
LEARNER_ROLE = "Training Learner"
MANAGER_ROLES = ("Training Manager", "System Manager")

# Assignment states that still need action from the employee
OPEN_STATUSES = ("Invited", "In Progress", "Course Completed", "Assessment Failed")


def same_user(a: str | None, b: str | None) -> bool:
	"""User IDs are emails; the database matches them ignoring case, so Python must too."""
	return bool(a and b) and a.strip().lower() == b.strip().lower()


def course_url(assignment: str) -> str:
	return get_url(f"{TRAINING_ROUTE}/course?a={assignment}")


def is_training_manager(user: str | None = None) -> bool:
	roles = frappe.get_roles(user or frappe.session.user)
	return any(r in roles for r in MANAGER_ROLES)


def logo_data_uri() -> str:
	"""Logo as a data URI so wkhtmltopdf never needs to fetch it over HTTP."""

	def _read():
		path = os.path.join(frappe.get_app_path("tridasa_dpdp"), "public", "images", "tridasa-logo.png")
		with open(path, "rb") as f:
			return "data:image/png;base64," + base64.b64encode(f.read()).decode()

	return frappe.cache.get_value("tridasa_dpdp:logo_data_uri", generator=_read)


def attempts_allowed(course, assignment) -> int:
	"""0 means unlimited."""
	if not course.max_attempts:
		return 0
	return course.max_attempts + (assignment.extra_attempts or 0)


def attempts_left(course, assignment) -> int | None:
	"""None means unlimited."""
	allowed = attempts_allowed(course, assignment)
	if not allowed:
		return None
	return max(allowed - (assignment.attempts_used or 0), 0)


def portal_context(context, require_login: bool = True):
	"""Common context for the /training pages."""
	from urllib.parse import quote

	import tridasa_dpdp

	user = frappe.session.user
	here = frappe.request.full_path.rstrip("?") if frappe.request else TRAINING_ROUTE
	context.login_url = "/login?redirect-to=" + quote(here)
	if require_login and user == "Guest":
		frappe.local.flags.redirect_location = context.login_url
		raise frappe.Redirect
	context.no_cache = 1
	context.no_breadcrumbs = 1
	context.user_full_name = frappe.utils.get_fullname(user) if user != "Guest" else ""
	context.is_desk_user = user != "Guest" and frappe.db.get_value("User", user, "user_type") == "System User"
	context.csrf_token = frappe.sessions.get_csrf_token() if user != "Guest" else ""
	context.academy_version = asset_version(tridasa_dpdp.__version__)
	return context


def asset_version(app_version: str) -> str:
	"""Cache-busting token for portal CSS/JS: app version plus the newest asset mtime."""
	public = os.path.join(frappe.get_app_path("tridasa_dpdp"), "public")
	files = ("css/academy.css", "js/academy_course.js", "images/skyline-night.svg")
	try:
		stamp = max(int(os.path.getmtime(os.path.join(public, f))) for f in files)
	except OSError:
		return app_version
	return f"{app_version}-{stamp}"


def safe_sendmail(**kwargs) -> bool:
	"""Send (queue) an email without letting a missing/broken outgoing account
	undo the enrolment or result that triggered it."""
	try:
		frappe.sendmail(**kwargs)
		return True
	except frappe.OutgoingEmailError:
		frappe.clear_last_message()
		frappe.log_error(
			title="Tridasa DPDP: email not sent",
			message="No default outgoing Email Account is set up (Settings > Email Account).\n\n"
			f"Subject: {kwargs.get('subject')}\nTo: {kwargs.get('recipients')}",
			reference_doctype=kwargs.get("reference_doctype"),
			reference_name=kwargs.get("reference_name"),
		)
		return False
