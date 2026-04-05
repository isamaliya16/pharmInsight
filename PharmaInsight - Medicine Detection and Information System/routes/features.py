"""
All 10 new feature routes in one blueprint.
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from database import get_db
import requests, json, re
from datetime import datetime

feat_bp = Blueprint("feat_bp", __name__)

# ── login guard ───────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*a, **kw)
    return dec

# ═══════════════════════════════════════════════════════════
# FEATURE 1 — Drug Interaction Checker
# ═══════════════════════════════════════════════════════════

INTERACTIONS_DB = {
    # (drugA_lower, drugB_lower): (severity, summary)
    ("warfarin","aspirin"):      ("SEVERE","Risk of serious bleeding. Both thin blood."),
    ("warfarin","ibuprofen"):    ("SEVERE","Increased bleeding risk."),
    ("metformin","alcohol"):     ("MODERATE","May increase risk of lactic acidosis."),
    ("metformin","ibuprofen"):   ("MODERATE","NSAIDs may reduce metformin effectiveness."),
    ("paracetamol","alcohol"):   ("MODERATE","Heavy alcohol use increases liver damage risk."),
    ("aspirin","ibuprofen"):     ("MODERATE","Both NSAIDs together increase GI bleed risk."),
    ("simvastatin","amiodarone"):("SEVERE","High risk of muscle damage (rhabdomyolysis)."),
    ("clopidogrel","omeprazole"):("MODERATE","Omeprazole reduces clopidogrel effectiveness."),
    ("ssri","tramadol"):         ("SEVERE","Risk of serotonin syndrome."),
    ("lisinopril","potassium"):  ("MODERATE","Risk of dangerously high potassium levels."),
    ("ciprofloxacin","antacids"):("MODERATE","Antacids reduce ciprofloxacin absorption."),
    ("digoxin","amiodarone"):    ("SEVERE","Amiodarone increases digoxin toxicity."),
    ("theophylline","ciprofloxacin"):("SEVERE","Ciprofloxacin increases theophylline toxicity."),
    ("atorvastatin","clarithromycin"):("SEVERE","Increased risk of muscle damage."),
    ("sildenafil","nitrates"):   ("SEVERE","Dangerous drop in blood pressure."),
}

@feat_bp.route("/interaction", methods=["GET","POST"])
@login_required
def interaction():
    result = None
    if request.method == "POST":
        d1 = request.form.get("drug1","").strip().lower()
        d2 = request.form.get("drug2","").strip().lower()
        if d1 and d2:
            key = tuple(sorted([d1, d2]))
            if key in INTERACTIONS_DB:
                severity, summary = INTERACTIONS_DB[key]
            else:
                # check partial matches
                matched = None
                for (a,b),(sev,txt) in INTERACTIONS_DB.items():
                    if (a in d1 or d1 in a) and (b in d2 or d2 in b):
                        matched = (sev, txt); break
                    if (b in d1 or d1 in b) and (a in d2 or d2 in a):
                        matched = (sev, txt); break
                if matched:
                    severity, summary = matched
                else:
                    severity, summary = ("LOW","No known significant interaction found. Always consult your doctor.")
            result = {"drug1": d1.title(), "drug2": d2.title(),
                      "severity": severity, "summary": summary}
            # log it
            conn = get_db()
            conn.execute(
                "INSERT INTO interaction_log (user_id,drug1,drug2,severity,summary) VALUES (?,?,?,?,?)",
                (session["user_id"], d1, d2, severity, summary))
            conn.commit(); conn.close()
    return render_template("interaction.html", result=result)


# ═══════════════════════════════════════════════════════════
# FEATURE 2 — Medicine Reminders
# ═══════════════════════════════════════════════════════════

@feat_bp.route("/reminders", methods=["GET","POST"])
@login_required
def reminders():
    conn = get_db()
    if request.method == "POST":
        action = request.form.get("action","add")
        if action == "add":
            conn.execute(
                "INSERT INTO reminders (user_id,medicine_name,dose,frequency,reminder_time,start_date,end_date) VALUES (?,?,?,?,?,?,?)",
                (session["user_id"],
                 request.form.get("medicine_name",""),
                 request.form.get("dose",""),
                 request.form.get("frequency",""),
                 request.form.get("reminder_time",""),
                 request.form.get("start_date",""),
                 request.form.get("end_date",""))
            )
            conn.commit()
        elif action == "delete":
            conn.execute("DELETE FROM reminders WHERE id=? AND user_id=?",
                         (request.form.get("id"), session["user_id"]))
            conn.commit()
        elif action == "toggle":
            conn.execute(
                "UPDATE reminders SET active = CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=? AND user_id=?",
                (request.form.get("id"), session["user_id"]))
            conn.commit()

    rows = conn.execute(
        "SELECT * FROM reminders WHERE user_id=? ORDER BY active DESC, reminder_time ASC",
        (session["user_id"],)).fetchall()
    conn.close()
    return render_template("reminders.html", reminders=rows)


# ═══════════════════════════════════════════════════════════
# FEATURE 3 — Prescription OCR Upload
# ═══════════════════════════════════════════════════════════

@feat_bp.route("/prescription", methods=["GET","POST"])
@login_required
def prescription():
    medicines_found = []
    ocr_text = ""
    if request.method == "POST":
        # Simulated OCR: parse textarea input as typed prescription
        raw = request.form.get("prescription_text","").strip()
        if raw:
            ocr_text = raw
            # Extract medicine-like words: capitalised or common patterns
            common = ["tab","cap","syp","inj","mg","ml","od","bd","tds","qid","sos"]
            lines = re.split(r'[\n,;]+', raw)
            for line in lines:
                line = line.strip()
                if not line: continue
                # Remove dosage numbers and units, get first word as medicine
                name = re.sub(r'\d+[\w.%/]*','', line).strip()
                name = re.sub(r'\b(' + '|'.join(common) + r')\b', '', name, flags=re.I).strip()
                name = re.split(r'\s+', name)[0].strip('.,()-').strip()
                if len(name) > 2:
                    medicines_found.append(name.title())
            medicines_found = list(dict.fromkeys(medicines_found))  # deduplicate
    return render_template("prescription.html",
                           medicines_found=medicines_found,
                           ocr_text=ocr_text)


# ═══════════════════════════════════════════════════════════
# FEATURE 4 — Order & Cart
# ═══════════════════════════════════════════════════════════

@feat_bp.route("/order", methods=["GET","POST"])
@login_required
def order():
    message = None
    if request.method == "POST":
        items_json = request.form.get("items_json","[]")
        address    = request.form.get("address","")
        total      = request.form.get("total","0")
        payment    = request.form.get("payment","COD")
        if items_json and address:
            conn = get_db()
            conn.execute(
                "INSERT INTO orders (user_id,items_json,address,total,payment,status) VALUES (?,?,?,?,?,?)",
                (session["user_id"], items_json, address, float(total), payment, "Placed"))
            conn.commit(); conn.close()
            message = "success"

    conn = get_db()
    my_orders = conn.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)).fetchall()
    conn.close()
    return render_template("order.html", my_orders=my_orders, message=message)


# ═══════════════════════════════════════════════════════════
# FEATURE 5 — Generic vs Brand Comparator
# ═══════════════════════════════════════════════════════════

GENERIC_DB = {
    "crocin":    {"generic":"Paracetamol 500mg","brand":"Crocin","brand_price":28,"generic_price":8,"manufacturer":"GSK","same_effect":True},
    "calpol":    {"generic":"Paracetamol 500mg","brand":"Calpol","brand_price":32,"generic_price":8,"manufacturer":"GSK","same_effect":True},
    "brufen":    {"generic":"Ibuprofen 400mg","brand":"Brufen","brand_price":45,"generic_price":12,"manufacturer":"Abbott","same_effect":True},
    "combiflam": {"generic":"Ibuprofen+Paracetamol","brand":"Combiflam","brand_price":55,"generic_price":18,"manufacturer":"Sanofi","same_effect":True},
    "zantac":    {"generic":"Ranitidine 150mg","brand":"Zantac","brand_price":60,"generic_price":15,"manufacturer":"GSK","same_effect":True},
    "omez":      {"generic":"Omeprazole 20mg","brand":"Omez","brand_price":75,"generic_price":22,"manufacturer":"Dr. Reddy","same_effect":True},
    "glucophage":{"generic":"Metformin 500mg","brand":"Glucophage","brand_price":90,"generic_price":25,"manufacturer":"Merck","same_effect":True},
    "augmentin": {"generic":"Amoxicillin+Clavulanate","brand":"Augmentin","brand_price":180,"generic_price":65,"manufacturer":"GSK","same_effect":True},
    "atorlip":   {"generic":"Atorvastatin 10mg","brand":"Atorlip","brand_price":120,"generic_price":38,"manufacturer":"Cipla","same_effect":True},
    "norvasc":   {"generic":"Amlodipine 5mg","brand":"Norvasc","brand_price":145,"generic_price":30,"manufacturer":"Pfizer","same_effect":True},
}

@feat_bp.route("/comparator", methods=["GET","POST"])
@login_required
def comparator():
    result = None
    if request.method == "POST":
        query = request.form.get("brand_name","").strip().lower()
        if query in GENERIC_DB:
            result = GENERIC_DB[query]
            result["query"] = query.title()
            result["savings"] = result["brand_price"] - result["generic_price"]
            result["savings_pct"] = round(result["savings"] * 100 / result["brand_price"], 1)
        else:
            # partial match
            for k, v in GENERIC_DB.items():
                if query in k or k in query:
                    result = v.copy()
                    result["query"] = query.title()
                    result["savings"] = result["brand_price"] - result["generic_price"]
                    result["savings_pct"] = round(result["savings"]*100/result["brand_price"],1)
                    break
            if not result:
                result = {"error": f'No comparison data found for "{query.title()}". Try: Crocin, Brufen, Omez, Augmentin, Atorlip'}
    return render_template("comparator.html", result=result)


# ═══════════════════════════════════════════════════════════
# FEATURE 6 — Symptom to Medicine Suggester
# ═══════════════════════════════════════════════════════════

SYMPTOM_MAP = {
    "fever":        [{"name":"Paracetamol","dose":"500mg every 6h","note":"Most common fever reducer"},
                     {"name":"Ibuprofen","dose":"400mg every 8h","note":"Also reduces inflammation"}],
    "headache":     [{"name":"Paracetamol","dose":"500–1000mg","note":"First-line for tension headache"},
                     {"name":"Aspirin","dose":"300–600mg","note":"Effective for migraines"}],
    "cold":         [{"name":"Cetirizine","dose":"10mg once daily","note":"For runny nose & sneezing"},
                     {"name":"Pseudoephedrine","dose":"60mg every 6h","note":"Nasal decongestant"}],
    "cough":        [{"name":"Dextromethorphan","dose":"15–30mg every 6h","note":"Dry cough suppressant"},
                     {"name":"Guaifenesin","dose":"200–400mg every 4h","note":"Productive cough expectorant"}],
    "acidity":      [{"name":"Omeprazole","dose":"20mg before breakfast","note":"Proton pump inhibitor"},
                     {"name":"Ranitidine","dose":"150mg twice daily","note":"H2 blocker for acid"}],
    "allergy":      [{"name":"Cetirizine","dose":"10mg once daily","note":"Non-drowsy antihistamine"},
                     {"name":"Loratadine","dose":"10mg once daily","note":"24-hour allergy relief"}],
    "pain":         [{"name":"Ibuprofen","dose":"400mg every 8h","note":"Anti-inflammatory pain relief"},
                     {"name":"Paracetamol","dose":"500mg every 6h","note":"Gentle on stomach"}],
    "diarrhea":     [{"name":"ORS","dose":"1 sachet in 1L water","note":"Rehydration first priority"},
                     {"name":"Loperamide","dose":"2mg after each loose stool","note":"Slows bowel movement"}],
    "vomiting":     [{"name":"Ondansetron","dose":"4–8mg every 8h","note":"Very effective antiemetic"},
                     {"name":"Domperidone","dose":"10mg before meals","note":"Promotes gastric motility"}],
    "diabetes":     [{"name":"Metformin","dose":"500mg twice daily with meals","note":"First-line oral hypoglycaemic"},
                     {"name":"Glipizide","dose":"5mg before breakfast","note":"Stimulates insulin release"}],
    "hypertension": [{"name":"Amlodipine","dose":"5mg once daily","note":"Calcium channel blocker"},
                     {"name":"Lisinopril","dose":"10mg once daily","note":"ACE inhibitor"}],
    "infection":    [{"name":"Amoxicillin","dose":"500mg three times daily","note":"Broad-spectrum antibiotic"},
                     {"name":"Azithromycin","dose":"500mg once daily for 3 days","note":"Z-pack regimen"}],
    "insomnia":     [{"name":"Melatonin","dose":"3–5mg at bedtime","note":"Natural sleep hormone"},
                     {"name":"Diphenhydramine","dose":"25–50mg at bedtime","note":"Short-term use only"}],
    "anxiety":      [{"name":"Alprazolam","dose":"0.25–0.5mg as needed","note":"Short-term only, controlled drug"},
                     {"name":"Buspirone","dose":"5mg twice daily","note":"Non-addictive anxiolytic"}],
}

@feat_bp.route("/symptoms", methods=["GET","POST"])
@login_required
def symptoms():
    suggestions = []
    entered = ""
    if request.method == "POST":
        entered = request.form.get("symptoms","").strip().lower()
        matched_keys = set()
        for symptom_key in SYMPTOM_MAP:
            if symptom_key in entered:
                for med in SYMPTOM_MAP[symptom_key]:
                    key = med["name"]
                    if key not in matched_keys:
                        suggestions.append({**med, "symptom": symptom_key.title()})
                        matched_keys.add(key)
    return render_template("symptoms.html", suggestions=suggestions, entered=entered)


# ═══════════════════════════════════════════════════════════
# FEATURE 7 — Personal Health Dashboard
# ═══════════════════════════════════════════════════════════

@feat_bp.route("/dashboard")
@login_required
def dashboard():
    uid  = session["user_id"]
    conn = get_db()

    total_searches = conn.execute(
        "SELECT COUNT(*) FROM search_history WHERE user_id=?", (uid,)).fetchone()[0]

    top_medicines = conn.execute(
        """SELECT medicine_name, COUNT(*) as cnt FROM search_history
           WHERE user_id=? GROUP BY medicine_name ORDER BY cnt DESC LIMIT 5""",
        (uid,)).fetchall()

    recent = conn.execute(
        "SELECT medicine_name, search_time FROM search_history WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (uid,)).fetchall()

    reminders_active = conn.execute(
        "SELECT COUNT(*) FROM reminders WHERE user_id=? AND active=1", (uid,)).fetchone()[0]

    orders_count = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE user_id=?", (uid,)).fetchone()[0]

    reviews_count = conn.execute(
        "SELECT COUNT(*) FROM reviews WHERE user_id=?", (uid,)).fetchone()[0]

    # searches per last 7 days for sparkline
    from datetime import timedelta
    daily = []
    for i in range(6,-1,-1):
        day = (datetime.now()-timedelta(days=i)).strftime("%Y-%m-%d")
        cnt = conn.execute(
            "SELECT COUNT(*) FROM search_history WHERE user_id=? AND DATE(search_time)=?",
            (uid, day)).fetchone()[0]
        daily.append({"date": day[-5:], "count": cnt})

    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()

    return render_template("dashboard.html",
        user=user,
        total_searches=total_searches,
        top_medicines=top_medicines,
        recent=recent,
        reminders_active=reminders_active,
        orders_count=orders_count,
        reviews_count=reviews_count,
        daily=daily)


# ═══════════════════════════════════════════════════════════
# FEATURE 8 — Language switcher (stored per user)
# ═══════════════════════════════════════════════════════════

@feat_bp.route("/set-language/<lang>")
def set_language(lang):
    if lang in ("en","hi","gu"):
        session["lang"] = lang
        if "user_id" in session:
            conn = get_db()
            conn.execute("UPDATE users SET language=? WHERE id=?", (lang, session["user_id"]))
            conn.commit(); conn.close()
    return redirect(request.referrer or "/")


# ═══════════════════════════════════════════════════════════
# FEATURE 9 — Reviews & Ratings
# ═══════════════════════════════════════════════════════════

@feat_bp.route("/reviews", methods=["GET","POST"])
@login_required
def reviews():
    message = None
    if request.method == "POST":
        action = request.form.get("action","add")
        if action == "add":
            medicine = request.form.get("medicine_name","").strip()
            rating   = request.form.get("rating","5")
            text     = request.form.get("review_text","").strip()
            if medicine and rating:
                conn = get_db()
                # One review per user per medicine
                existing = conn.execute(
                    "SELECT id FROM reviews WHERE user_id=? AND medicine_name=?",
                    (session["user_id"], medicine)).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE reviews SET rating=?, review_text=? WHERE id=?",
                        (int(rating), text, existing["id"]))
                    message = "updated"
                else:
                    conn.execute(
                        "INSERT INTO reviews (user_id,medicine_name,rating,review_text) VALUES (?,?,?,?)",
                        (session["user_id"], medicine, int(rating), text))
                    message = "added"
                conn.commit(); conn.close()
        elif action == "delete":
            conn = get_db()
            conn.execute("DELETE FROM reviews WHERE id=? AND user_id=?",
                         (request.form.get("id"), session["user_id"]))
            conn.commit(); conn.close()

    conn = get_db()
    # all reviews with user name joined
    all_reviews = conn.execute(
        """SELECT r.*, u.name as user_name
           FROM reviews r JOIN users u ON u.id=r.user_id
           ORDER BY r.id DESC""").fetchall()
    my_reviews = conn.execute(
        "SELECT * FROM reviews WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)).fetchall()
    # avg ratings per medicine
    avg_ratings = conn.execute(
        "SELECT medicine_name, ROUND(AVG(rating),1) as avg, COUNT(*) as cnt FROM reviews GROUP BY medicine_name ORDER BY avg DESC"
    ).fetchall()
    conn.close()
    return render_template("reviews.html",
                           all_reviews=all_reviews,
                           my_reviews=my_reviews,
                           avg_ratings=avg_ratings,
                           message=message)


# ═══════════════════════════════════════════════════════════
# FEATURE 10 — AI Chatbot API endpoint
# ═══════════════════════════════════════════════════════════

MEDICINE_QA = {
    "paracetamol": "Paracetamol (Acetaminophen) is used for pain and fever. Usual adult dose is 500mg–1g every 4–6 hours. Max 4g/day. Avoid alcohol. Safe in pregnancy when used as directed.",
    "ibuprofen":   "Ibuprofen is an NSAID used for pain, fever and inflammation. Take 200–400mg every 4–8 hours with food. Avoid if you have kidney disease, stomach ulcers, or are pregnant.",
    "amoxicillin": "Amoxicillin is a penicillin antibiotic. Usual dose: 250–500mg three times daily for 7–14 days. Complete the full course. Inform doctor if allergic to penicillin.",
    "metformin":   "Metformin is for type 2 diabetes. Take 500mg twice daily with meals to reduce stomach upset. Avoid alcohol. Do not take if kidney function is impaired.",
    "cetirizine":  "Cetirizine is an antihistamine for allergies. Take 10mg once daily. May cause mild drowsiness. Safe for most adults and children over 6.",
    "omeprazole":  "Omeprazole reduces stomach acid. Take 20mg 30 minutes before breakfast. Used for GERD, ulcers, and heartburn. Long-term use may reduce B12 absorption.",
    "aspirin":     "Aspirin has pain-relieving, fever-reducing, and blood-thinning effects. Avoid in children under 16 (Reye's syndrome risk). Can cause stomach upset.",
    "atorvastatin":"Atorvastatin lowers cholesterol. Take 10–80mg once daily, usually at bedtime. Report muscle pain immediately. Avoid grapefruit juice.",
    "amlodipine":  "Amlodipine treats high blood pressure and chest pain. Take 5–10mg once daily. May cause ankle swelling and flushing. Do not stop suddenly.",
    "azithromycin":"Azithromycin is a macrolide antibiotic. Standard dose: 500mg day 1, then 250mg for 4 days. Take on an empty stomach. Avoid antacids.",
    "side effect":  "Side effects vary by medicine. Common ones include nausea, dizziness, or drowsiness. Always read the package insert and consult your doctor if severe.",
    "dosage":       "Dosage depends on age, weight, kidney/liver function, and condition. Always follow the prescribed dose. Never double-dose if you miss one.",
    "interaction":  "Drug interactions can be dangerous. Always tell your doctor and pharmacist about ALL medicines you take, including supplements and OTC drugs.",
    "pregnancy":    "During pregnancy, only take medicines recommended by your doctor. Paracetamol is generally safest. Avoid NSAIDs, especially in third trimester.",
    "alcohol":      "Many medicines interact with alcohol. Alcohol should be avoided with paracetamol (liver risk), metformin (lactic acidosis), and sedatives.",
    "storage":      "Most medicines should be stored below 25°C, away from sunlight and moisture. Do not store in the bathroom. Keep out of reach of children.",
    "expired":      "Never use expired medicines. Effectiveness decreases and some can become harmful after expiry. Return unused medicines to a pharmacy for safe disposal.",
    "overdose":     "If you suspect a medicine overdose, call emergency services immediately (India: 112). Do not induce vomiting unless instructed by a medical professional.",
    "generic":      "Generic medicines contain the same active ingredient as branded versions at a fraction of the cost. They are equally effective and approved by regulators.",
    "antibiotic":   "Always complete a full antibiotic course even if you feel better. Never take leftover antibiotics. Stopping early causes antibiotic resistance.",
}

@feat_bp.route("/chatbot", methods=["POST"])
def chatbot():
    user_msg = request.json.get("message","").strip().lower()
    if not user_msg:
        return jsonify({"reply":"Please type a question about a medicine."})

    # Find best match
    best_reply = None
    for keyword, answer in MEDICINE_QA.items():
        if keyword in user_msg:
            best_reply = answer
            break

    if not best_reply:
        # generic fallback
        if any(w in user_msg for w in ["hello","hi","hey"]):
            best_reply = "Hello! I'm MediBot 🤖. Ask me anything about medicines — dosage, side effects, interactions, storage, and more!"
        elif any(w in user_msg for w in ["thank","thanks"]):
            best_reply = "You're welcome! Stay healthy 💊. Remember to always consult a doctor for personalised advice."
        else:
            best_reply = (
                f"I don't have specific information about '{user_msg.title()}' yet. "
                "Try asking about a specific medicine name (e.g. Paracetamol, Ibuprofen), "
                "or topics like: dosage, side effects, interactions, pregnancy, storage, or overdose. "
                "⚠️ Always consult a qualified doctor for medical advice."
            )

    disclaimer = " ⚕️ <em>This is general information only — not a substitute for professional medical advice.</em>"
    return jsonify({"reply": best_reply + disclaimer})
