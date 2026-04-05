from flask import Blueprint, render_template, session, redirect, url_for
from database import get_db

history_bp = Blueprint("history_bp", __name__)

@history_bp.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    rows = conn.execute("""
        SELECT medicine_name, search_type, search_time
        FROM search_history
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()
    conn.close()

    return render_template("history.html", history=rows)


@history_bp.route("/clear-history")
def clear_history():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    conn.execute("DELETE FROM search_history WHERE user_id=?", (session["user_id"],))
    conn.commit()
    conn.close()

    return redirect(url_for("history_bp.history"))
