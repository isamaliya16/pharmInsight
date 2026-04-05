from flask import Blueprint, render_template, session, redirect, url_for
from database import get_db

account_bp = Blueprint("account_bp", __name__)

@account_bp.route("/account")
def account():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    # Bug fix: was selecting phone + created_at which didn't exist in old DB schema
    user = conn.execute(
        "SELECT name, email, phone, created_at FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    return render_template("account.html", user=user)
