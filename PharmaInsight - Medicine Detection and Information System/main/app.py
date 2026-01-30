from flask import Flask, render_template, request, redirect, url_for, session
import requests
import sqlite3
import re

app = Flask(__name__)
app.secret_key = "8f$9#@!kL90sPqW@123"


# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn
    
def create_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            phone VARCHAR(15) NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


create_table()


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/index")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")

# ---------------- MEDICINE SEARCH (TEXT / VOICE ONLY) ----------------
@app.route("/search", methods=["GET", "POST"])
def search():
    medicine_data = None
    error = None

    if request.method == "POST":
        medicine_name = request.form.get("medicine", "").strip()

        if not medicine_name:
            error = "Please provide medicine name"
            return render_template("search.html", error=error)

        try:
            url = "https://api.fda.gov/drug/label.json"
            params = {
                "search": f'openfda.brand_name:"{medicine_name}" OR openfda.generic_name:"{medicine_name}"',
                "limit": 1
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                error = f"No data found for '{medicine_name}'"
                return render_template("search.html", error=error)

            data = response.json()

            if "results" not in data or not data["results"]:
                error = f"No information available for '{medicine_name}'"
                return render_template("search.html", error=error)

            result = data["results"][0]
            openfda = result.get("openfda", {})

            # ✅ Helper to safely join text
            def safe_join(value):
                if isinstance(value, list):
                    return " ".join(value)
                return value if value else "N/A"

            # ✅ Format FDA date
            def format_date(d):
                if d and len(d) == 8:
                    return f"{d[6:8]}-{d[4:6]}-{d[:4]}"
                return "N/A"

            medicine_data = {
                # 🔹 Identification
                "brand_name": ", ".join(openfda.get("brand_name", ["N/A"])),
                "generic_name": ", ".join(openfda.get("generic_name", ["N/A"])),
                "substance_name": ", ".join(openfda.get("substance_name", ["N/A"])),
                "manufacturer": ", ".join(openfda.get("manufacturer_name", ["N/A"])),
                "product_type": ", ".join(openfda.get("product_type", ["N/A"])),

                # 🔹 Classification
                "route": ", ".join(openfda.get("route", ["N/A"])),
                "dosage_form": ", ".join(openfda.get("dosage_form", ["N/A"])),
                "pharmacologic_class": ", ".join(openfda.get("pharm_class_epc", ["N/A"])),
                "dea_schedule": ", ".join(openfda.get("dea_schedule", ["N/A"])),

                # 🔹 Usage
                "purpose": safe_join(result.get("purpose")),
                "indications_and_usage": safe_join(result.get("indications_and_usage")),
                "dosage_and_administration": safe_join(result.get("dosage_and_administration")),
                "how_supplied": safe_join(result.get("how_supplied")),

                # 🔹 Safety
                "warnings": safe_join(result.get("warnings")),
                "boxed_warning": safe_join(result.get("boxed_warning")),
                "contraindications": safe_join(result.get("contraindications")),
                "adverse_reactions": safe_join(result.get("adverse_reactions")),
                "drug_interactions": safe_join(result.get("drug_interactions")),
                "overdosage": safe_join(result.get("overdosage")),

                # 🔹 Special population
                "pregnancy": safe_join(result.get("pregnancy")),
                "lactation": safe_join(result.get("lactation")),
                "pediatric_use": safe_join(result.get("pediatric_use")),
                "geriatric_use": safe_join(result.get("geriatric_use")),

                # 🔹 Pharmacology
                "mechanism_of_action": safe_join(result.get("mechanism_of_action")),
                "pharmacodynamics": safe_join(result.get("pharmacodynamics")),
                "pharmacokinetics": safe_join(result.get("pharmacokinetics")),

                # 🔹 Storage
                "storage_and_handling": safe_join(result.get("storage_and_handling")),

                # 🔹 Regulatory
                "spl_id": ", ".join(openfda.get("spl_id", ["N/A"])),
                "application_number": ", ".join(openfda.get("application_number", ["N/A"])),

                # 🔹 Meta
                "last_updated": format_date(result.get("effective_time")),
            }

        except requests.exceptions.Timeout:
            error = "FDA service timeout. Please try again."

        except Exception as e:
            error = "Unexpected error while fetching medicine data"

    return render_template("search.html", medicine=medicine_data, error=error)


# ---------------- SEARCH HISTORY ----------------
@app.route("/history")
def history():
    return render_template("history.html")


# ---------------- CONTACT ----------------
@app.route("/contact")
def contact():
    return render_template("contact.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if password != confirm:
            return redirect("/register?error=1")

        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users (name, email, phone, password) VALUES (?,?,?,?)",
                (name, email, phone, password)
            )
            conn.commit()
            conn.close()
            return redirect("/register?success=1")

        except sqlite3.IntegrityError:
            return redirect("/register?error=1")

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect("/index")
        else:
            return redirect("/login?error=1")

    return render_template("login.html")


# ---------------- ACCOUNT ----------------
@app.route("/account")
def account():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    user = conn.execute(
        "SELECT name, email, phone FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    return render_template("account.html", user=user)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
