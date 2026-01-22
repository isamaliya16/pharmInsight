from flask import Flask, render_template, request
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

# ---------------- HOME ----------------
@app.route("/index")
def index():
    return render_template("index.html")

# ---------------- ABOUT ----------------
@app.route("/about")
def about():
    return render_template("about.html")

# ---------------- MEDICINE SEARCH ----------------
@app.route("/search", methods=["GET", "POST"])
def search():
    medicine_data = None
    error = None

    if request.method == "POST":
        medicine_name = request.form.get("medicine")

        if not medicine_name:
            error = "Please enter a medicine name"
        else:
            try:
                url = "https://api.fda.gov/drug/label.json"
                params = {
                    "search": f'openfda.brand_name:"{medicine_name}" OR openfda.generic_name:"{medicine_name}"',
                    "limit": 1
                }

                response = requests.get(url, params=params)

                if response.status_code != 200:
                    error = "Medicine not found"
                else:
                    data = response.json()
                    result = data["results"][0]
                    openfda = result.get("openfda", {})

                    medicine_data = {
    # Basic Identity
    "brand": ", ".join(openfda.get("brand_name", ["N/A"])),
    "generic": ", ".join(openfda.get("generic_name", ["N/A"])),
    "manufacturer": ", ".join(openfda.get("manufacturer_name", ["N/A"])),
    "route": ", ".join(openfda.get("route", ["N/A"])),
    "dosage_form": ", ".join(openfda.get("dosage_form", ["N/A"])),
    "product_type": ", ".join(openfda.get("product_type", ["N/A"])),

    # Medical Information
    "purpose": " ".join(result.get("purpose", ["N/A"])),
    "uses": " ".join(result.get("indications_and_usage", ["N/A"])),
    "dosage": " ".join(result.get("dosage_and_administration", ["N/A"])),
    "warnings": " ".join(result.get("warnings", ["N/A"])),
    "side_effects": " ".join(result.get("adverse_reactions", ["N/A"])),

    # Safety Information
    "pregnancy_warning": " ".join(result.get("pregnancy", ["N/A"])),
    "lactation_warning": " ".join(result.get("nursing_mothers", ["N/A"])),
    "pediatric_use": " ".join(result.get("pediatric_use", ["N/A"])),
    "geriatric_use": " ".join(result.get("geriatric_use", ["N/A"])),

    # Drug Interaction & Contraindication
    "drug_interactions": " ".join(result.get("drug_interactions", ["N/A"])),
    "contraindications": " ".join(result.get("contraindications", ["N/A"])),

    # Usage & Handling
    "how_supplied": " ".join(result.get("how_supplied", ["N/A"])),
    "storage": " ".join(result.get("storage_and_handling", ["N/A"])),
    "overdose": " ".join(result.get("overdosage", ["N/A"])),

    # Clinical / Scientific
    "mechanism_of_action": " ".join(result.get("mechanism_of_action", ["N/A"])),
    "pharmacodynamics": " ".join(result.get("pharmacodynamics", ["N/A"])),
    "pharmacokinetics": " ".join(result.get("pharmacokinetics", ["N/A"])),
}


            except:
                error = "Error fetching medicine data"

    return render_template("search.html", medicine=medicine_data, error=error)

# ---------------- SEARCH HISTORY ----------------
@app.route("/history")
def history():
    return render_template("history.html")

# ---------------- CONTACT ----------------
@app.route("/contact")
def contact():
    return render_template("contact.html")

# ---------------- LOGIN ----------------
@app.route("/login")
def login():
    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register")
def register():
    return render_template("register.html")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
