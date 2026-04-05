from flask import Blueprint, request, redirect, url_for, flash
from database import save_contact

contact_bp = Blueprint("contact_bp", __name__)

# Bug fix: save_contact didn't exist in old database.py — now added
@contact_bp.route("/contact", methods=["POST"])
def contact():
    name    = request.form.get("name", "").strip()
    email   = request.form.get("email", "").strip()
    subject = request.form.get("subject", "").strip()
    message = request.form.get("message", "").strip()

    if name and email and message:
        save_contact(name, email, subject, message)

    # Bug fix: was redirecting to admin — redirect to home with success
    return redirect(url_for("home.index") + "?msg=sent")
