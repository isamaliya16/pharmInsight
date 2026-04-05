from flask import Blueprint, render_template

misc_bp = Blueprint("misc", __name__)

# Bug fix: /contact GET route was duplicated with contact_bp POST route
# This file now only serves the GET (page render)
@misc_bp.route("/contact")
def contact():
    return render_template("contact.html")
