import frappe


def execute():
	"""Assignments created before invitations became a separate step were emailed on creation."""
	frappe.db.sql(
		"""UPDATE `tabTraining Assignment` SET invitation_emailed_on = invited_on
		WHERE invitation_emailed_on IS NULL AND invited_on IS NOT NULL"""
	)
