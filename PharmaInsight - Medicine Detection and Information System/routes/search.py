from flask import Blueprint, render_template, session, redirect, request, url_for
from functools import wraps
import requests
from database import get_db

search_bp = Blueprint("search_bp", __name__)


def login_required(f):
    @wraps(f)   # Bug fix: original wrapper didn't use functools.wraps, broke Flask routing
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@search_bp.route("/search", methods=["GET", "POST"])
@login_required
def search():
    medicine_data = None
    error         = None

    if request.method == "POST":
        medicine_name = request.form.get("medicine", "").strip()

        if not medicine_name:
            error = "Please enter a medicine name."
            return render_template("search.html", error=error)

        # Save search history
        conn = get_db()
        conn.execute(
            "INSERT INTO search_history (user_id, medicine_name, search_type) VALUES (?,?,?)",
            (session["user_id"], medicine_name, "Text Search")
        )
        conn.commit()
        conn.close()

        # Fetch from FDA API
        try:
            url    = "https://api.fda.gov/drug/label.json"
            params = {
                "search": (
                    f'openfda.brand_name:"{medicine_name}"'
                    f' OR openfda.generic_name:"{medicine_name}"'
                ),
                "limit": 1
            }
            response = requests.get(url, params=params, timeout=10)
            data     = response.json()

            if "results" in data:
                r       = data["results"][0]
                openfda = r.get("openfda", {})

                def first(lst): return lst[0] if lst else "N/A"
                def join(lst):  return ", ".join(lst) if lst else "N/A"
                def section(key): return " ".join(r.get(key, ["N/A"]))

                medicine_data = {
                    "brand_name"              : join(openfda.get("brand_name")),
                    "generic_name"            : join(openfda.get("generic_name")),
                    "substance_name"          : join(openfda.get("substance_name")),
                    "manufacturer"            : join(openfda.get("manufacturer_name")),
                    "product_type"            : join(openfda.get("product_type")),
                    "route"                   : join(openfda.get("route")),
                    "dosage_form"             : join(openfda.get("dosage_form")),
                    # sections
                    "purpose"                 : section("purpose"),
                    "indications_and_usage"   : section("indications_and_usage"),
                    "dosage_and_administration": section("dosage_and_administration"),
                    "warnings"                : section("warnings"),
                    "boxed_warning"           : section("boxed_warning"),
                    "contraindications"       : section("contraindications"),
                    "adverse_reactions"       : section("adverse_reactions"),
                    "drug_interactions"       : section("drug_interactions"),
                    "overdosage"              : section("overdosage"),
                    "pregnancy"               : section("pregnancy"),
                    "lactation"               : section("lactation"),
                    "pediatric_use"           : section("pediatric_use"),
                    "geriatric_use"           : section("geriatric_use"),
                    "mechanism_of_action"     : section("mechanism_of_action"),
                    "pharmacodynamics"        : section("pharmacodynamics"),
                    "pharmacokinetics"        : section("pharmacokinetics"),
                    "storage_and_handling"    : section("storage_and_handling"),
                    "dea_schedule"            : join(openfda.get("schedule")),
                    "application_number"      : join(openfda.get("application_number")),
                    "spl_id"                  : first(openfda.get("spl_id", [])),
                    "last_updated"            : r.get("effective_time", "N/A"),
                }
            else:
                error = f'No data found for "{medicine_name}" in FDA database.'

        except requests.exceptions.Timeout:
            error = "FDA service timed out. Please try again."
        except requests.exceptions.ConnectionError:
            error = "Could not connect to FDA service. Check your internet connection."
        except Exception as e:
            error = f"An error occurred: {str(e)}"

    return render_template("search.html", medicine=medicine_data, error=error,
                           user_name=session.get("user_name", ""))
