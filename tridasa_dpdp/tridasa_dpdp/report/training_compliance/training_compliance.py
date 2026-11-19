# Copyright (c) 2026, Tridasa Realty Ventures Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Per-department funnel: invited → read slides → attempted → certified, plus overdue."""

import frappe
from frappe import _

OPEN = ("Invited", "In Progress", "Course Completed", "Assessment Failed")
GROUPS = {"Department": "department", "Branch": "branch", "Designation": "designation", "Company": "company"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	group_field = GROUPS.get(filters.group_by or "Department", "department")
	rows = get_rows(filters, group_field)
	return get_columns(filters.group_by or "Department"), rows, None, get_chart(rows), get_summary(rows)


def get_columns(group_label):
	def col(fieldname, label, fieldtype="Int", width=110, **kw):
		return {"fieldname": fieldname, "label": _(label), "fieldtype": fieldtype, "width": width, **kw}

	return [
		col("group", group_label, "Data", 220),
		col("invited", "Invited"),
		col("not_started", "Not Started"),
		col("reading", "Reading Slides", width=120),
		col("slides_done", "Slides Completed", width=130),
		col("attempted", "Attempted Assessment", width=160),
		col("failed", "Failed / Retake"),
		col("certified", "Certified"),
		col("pending", "Pending"),
		col("overdue", "Overdue"),
		col("completion", "Completion %", "Percent", 120),
		col("avg_score", "Avg Best Score", "Percent", 120),
	]


def get_rows(filters, group_field):
	conditions = {"status": ("!=", "Cancelled")}
	for f in ("course", "company", "department"):
		if filters.get(f):
			conditions[f] = filters[f]
	data = frappe.get_all(
		"Training Assignment",
		filters=conditions,
		fields=[group_field + " as grp", "status", "overdue", "attempts_used", "best_score"],
	)
	groups = {}
	for r in data:
		g = groups.setdefault(r.grp or _("Not set"), frappe._dict(scores=[], **{k: 0 for k in (
			"invited", "not_started", "reading", "slides_done", "attempted", "failed", "certified", "pending", "overdue")}))
		g.invited += 1
		g.not_started += r.status == "Invited"
		g.reading += r.status == "In Progress"
		g.slides_done += r.status in ("Course Completed", "Assessment Failed", "Certified")
		g.attempted += bool(r.attempts_used)
		g.failed += r.status == "Assessment Failed"
		g.certified += r.status == "Certified"
		g.pending += r.status in OPEN or r.status == "Expired"
		g.overdue += bool(r.overdue)
		if r.attempts_used:
			g.scores.append(r.best_score or 0)

	out = []
	for name, g in sorted(groups.items(), key=lambda kv: kv[0]):
		scores = g.pop("scores")
		g.group = name
		g.completion = round(g.certified * 100 / g.invited, 1) if g.invited else 0
		g.avg_score = round(sum(scores) / len(scores), 1) if scores else None
		out.append(g)
	return out


def get_chart(rows):
	if not rows:
		return None
	return {
		"data": {
			"labels": [r.group for r in rows],
			"datasets": [
				{"name": _("Certified"), "values": [r.certified for r in rows]},
				{"name": _("Attempted, not certified"), "values": [r.attempted - r.certified for r in rows]},
				{"name": _("Not attempted"), "values": [r.invited - r.attempted for r in rows]},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
		"colors": ["#1E7A4F", "#E44B47", "#9AA3AE"],
	}


def get_summary(rows):
	total = sum(r.invited for r in rows)
	certified = sum(r.certified for r in rows)
	attempted = sum(r.attempted for r in rows)
	overdue = sum(r.overdue for r in rows)
	return [
		{"label": _("Invited"), "value": total, "indicator": "Blue", "datatype": "Int"},
		{"label": _("Completed slides"), "value": sum(r.slides_done for r in rows), "indicator": "Purple", "datatype": "Int"},
		{"label": _("Attempted assessment"), "value": attempted, "indicator": "Orange", "datatype": "Int"},
		{"label": _("Certified"), "value": certified, "indicator": "Green", "datatype": "Int"},
		{"label": _("Overdue"), "value": overdue, "indicator": "Red", "datatype": "Int"},
		{"label": _("Completion"), "value": round(certified * 100 / total, 1) if total else 0, "indicator": "Green", "datatype": "Percent"},
	]
