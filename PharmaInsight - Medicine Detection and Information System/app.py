from flask import Flask
from config import Config
from database import create_tables, get_db

from routes.home     import home_bp
from routes.search   import search_bp
from routes.auth     import auth_bp
from routes.admin    import admin_bp
from routes.misc     import misc_bp
from routes.history  import history_bp
from routes.account  import account_bp
from routes.contact  import contact_bp
from routes.features import feat_bp

app = Flask(__name__)
app.config.from_object(Config)

create_tables()

for bp in [home_bp, search_bp, auth_bp, admin_bp, misc_bp,
           history_bp, account_bp, contact_bp, feat_bp]:
    app.register_blueprint(bp)

def _print_startup_info():
    conn = get_db()
    admin = conn.execute("SELECT email,password FROM users WHERE is_admin=1 LIMIT 1").fetchone()
    conn.close()
    line = "=" * 54
    print(line)
    print("  PharmaInsight  —  Server Started")
    print(line)
    print(f"  URL  :  http://localhost:5000")
    if admin:
        print(f"  ADMIN (keep private):")
        print(f"    Email    : {admin['email']}")
        print(f"    Password : {admin['password']}")
    print(line + "\n")

if __name__ == "__main__":
    _print_startup_info()
    app.run(debug=True)
