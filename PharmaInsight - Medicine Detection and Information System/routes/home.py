from flask import Blueprint, render_template, request
from database import log_visitor

# Bug fix: Blueprint name was "home" but url_for("home.index") was used — keep consistent
home_bp = Blueprint("home", __name__)

@home_bp.route("/")
@home_bp.route("/index")
def index():
    log_visitor()
    return render_template("index.html")

@home_bp.route("/about")
def about():
    return render_template("about.html")
