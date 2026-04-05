from flask import Blueprint, render_template, request, redirect, session, url_for
from database import get_db
import sqlite3

auth_bp = Blueprint("auth", __name__)


# ─────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Already logged in → go to search
    if "user_id" in session:
        return redirect(url_for("search_bp.search"))

    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            session["is_admin"]  = bool(user["is_admin"])   # store admin flag in session
            return redirect(url_for("search_bp.search"))
        else:
            error = "Invalid email or password. Please try again."

    return render_template("login.html", error=error)


# ─────────────────────────────────────────────
#  REGISTER  (normal users only — is_admin=0)
# ─────────────────────────────────────────────
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name             = request.form.get("name", "").strip()
        email            = request.form.get("email", "").strip()
        phone            = request.form.get("phone", "").strip()
        password         = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if password != confirm_password:
            error = "Passwords do not match."
            return render_template("register.html", error=error)

        try:
            conn = get_db()
            # is_admin is always 0 for registered users — admins are seeded by DB only
            conn.execute(
                "INSERT INTO users (name, email, phone, password, is_admin) VALUES (?,?,?,?,0)",
                (name, email, phone, password)
            )
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            conn.close()

            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            session["is_admin"]  = False
            return redirect(url_for("search_bp.search"))

        except sqlite3.IntegrityError:
            error = "Email already registered. Please login."

    return render_template("register.html", error=error)


# ─────────────────────────────────────────────
#  LOGOUT
# ─────────────────────────────────────────────
@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
