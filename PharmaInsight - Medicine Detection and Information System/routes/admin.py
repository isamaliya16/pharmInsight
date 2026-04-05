from flask import Blueprint, render_template, jsonify, redirect, url_for, session, flash
from database import get_db
from datetime import datetime, timedelta
from functools import wraps

admin_bp = Blueprint("admin_bp", __name__)


# ══════════════════════════════════════════════
#  ADMIN-ONLY GUARD  ← the security layer
# ══════════════════════════════════════════════

def admin_required(f):
    """Decorator: only users with is_admin=True in session can proceed.
    Anyone else (logged-out, normal user) is redirected with an error."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            # Not logged in at all
            return redirect(url_for("auth.login") + "?next=admin&error=login")
        if not session.get("is_admin"):
            # Logged in but NOT an admin → hard block
            return redirect(url_for("admin_bp.access_denied"))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/admin/denied")
def access_denied():
    """Shown to any non-admin who tries to reach the admin panel."""
    return render_template("admin_denied.html"), 403


# ══════════════════════════════════════════════
#  ADMIN DASHBOARD
# ══════════════════════════════════════════════

@admin_bp.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db()
    cursor = conn.cursor()

    total_users    = cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0]
    total_searches = cursor.execute("SELECT COUNT(*) FROM search_history").fetchone()[0]
    total_visitors = cursor.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]

    top_medicine = cursor.execute("""
        SELECT medicine_name, COUNT(*) as count
        FROM search_history
        GROUP BY medicine_name
        ORDER BY count DESC LIMIT 1
    """).fetchone()

    top_medicines = cursor.execute("""
        SELECT medicine_name, COUNT(*) as count
        FROM search_history
        GROUP BY medicine_name
        ORDER BY count DESC LIMIT 5
    """).fetchall()

    last_7_days = []
    for i in range(6, -1, -1):
        day    = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        result = cursor.execute(
            "SELECT COUNT(*) FROM search_history WHERE DATE(search_time)=?", (day,)
        ).fetchone()[0]
        last_7_days.append((day, result))

    monthly_usage = cursor.execute("""
        SELECT strftime('%Y-%m', search_time) as month, COUNT(*) as total
        FROM search_history GROUP BY month ORDER BY month ASC
    """).fetchall()

    yearly_usage = cursor.execute("""
        SELECT strftime('%Y', search_time) as year, COUNT(*) as total
        FROM search_history GROUP BY year ORDER BY year ASC
    """).fetchall()

    recent_activity = cursor.execute("""
        SELECT users.name, search_history.medicine_name, search_history.search_time
        FROM search_history
        JOIN users ON users.id = search_history.user_id
        ORDER BY search_history.id DESC LIMIT 10
    """).fetchall()

    # Exclude admin accounts from user list
    users = cursor.execute("""
        SELECT id, name, email, created_at FROM users
        WHERE is_admin=0 ORDER BY id DESC
    """).fetchall()

    messages = cursor.execute(
        "SELECT * FROM contact_messages ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        total_users=total_users,
        total_searches=total_searches,
        total_visitors=total_visitors,
        top_medicine=top_medicine,
        top_medicines=top_medicines,
        daily_usage=last_7_days,
        monthly_usage=monthly_usage,
        yearly_usage=yearly_usage,
        recent_activity=recent_activity,
        users=users,
        messages=messages
    )


# ══════════════════════════════════════════════
#  DELETE USER
# ══════════════════════════════════════════════

@admin_bp.route("/delete_user/<int:user_id>")
@admin_required
def delete_user(user_id):
    conn = get_db()
    # Safety: never allow deleting another admin
    target = conn.execute("SELECT is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    if target and target["is_admin"] == 1:
        conn.close()
        return redirect(url_for("admin_bp.admin_dashboard"))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_bp.admin_dashboard"))


# ══════════════════════════════════════════════
#  DELETE MESSAGE
# ══════════════════════════════════════════════

@admin_bp.route("/delete_message/<int:msg_id>")
@admin_required
def delete_message(msg_id):
    conn = get_db()
    conn.execute("DELETE FROM contact_messages WHERE id=?", (msg_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_bp.admin_dashboard"))


# ══════════════════════════════════════════════
#  CHART DATA API  (also admin-only)
# ══════════════════════════════════════════════

@admin_bp.route("/admin/chart-data")
@admin_required
def chart_data():
    conn = get_db()
    cursor = conn.cursor()

    pie_data = cursor.execute("""
        SELECT medicine_name, COUNT(*) as total
        FROM search_history
        GROUP BY medicine_name ORDER BY total DESC LIMIT 6
    """).fetchall()

    daily_labels, daily_values = [], []
    for i in range(6, -1, -1):
        day   = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        count = cursor.execute(
            "SELECT COUNT(*) FROM search_history WHERE DATE(search_time)=?", (day,)
        ).fetchone()[0]
        daily_labels.append(day[-5:])   # MM-DD
        daily_values.append(count)

    monthly_data = cursor.execute("""
        SELECT strftime('%Y-%m', search_time) as month, COUNT(*) as total
        FROM search_history GROUP BY month ORDER BY month ASC
    """).fetchall()

    yearly_data = cursor.execute("""
        SELECT strftime('%Y', search_time) as year, COUNT(*) as total
        FROM search_history GROUP BY year ORDER BY year ASC
    """).fetchall()

    conn.close()

    total_pie = sum(x[1] for x in pie_data) or 1   # avoid division by zero

    return jsonify({
        "pie_labels" : [x[0] for x in pie_data],
        "pie_values" : [x[1] for x in pie_data],
        # Pre-computed percentages for the chart labels
        "pie_pcts"   : [round(x[1] * 100 / total_pie, 1) for x in pie_data],

        "daily_labels" : daily_labels,
        "daily_values" : daily_values,

        "monthly_labels": [x[0] for x in monthly_data],
        "monthly_values": [x[1] for x in monthly_data],

        "yearly_labels" : [x[0] for x in yearly_data],
        "yearly_values" : [x[1] for x in yearly_data],
    })
