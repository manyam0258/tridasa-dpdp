def certificate_website_permission(doc, ptype, user, verbose=False):
	"""Lets a learner open/print their own certificate (used by print view & PDF)."""
	return ptype in ("read", "print") and doc.user == user and doc.status != "Revoked"
