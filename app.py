from flask import Flask, render_template, abort, request, jsonify, session, redirect, url_for
from pathlib import Path
from datetime import datetime, date
from dotenv import load_dotenv
import frontmatter
import markdown
import re
import json
import os
import secrets
import tarfile
import threading
import time
import requests as http_requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

BLOG_DIR = Path("content/blog")
OUTDATED_CUTOFF = date(2026, 1, 1)
DATA_FILE = Path("data.json")
SIGNUPS_FILE = Path("signups.txt")
BACKUPS_DIR = Path("backups")
APPLICATIONS_FILE = Path("applications.json")

DISCORD_WEBHOOK = os.environ.get(
    "DISCORD_WEBHOOK",
    "https://discord.com/api/webhooks/1504789105714925661/e4-Pq_eF89ksaEQs2zwWx01rfKQbd70cwyFxxhIUZQN1OTIxXRoVryEHLUy5ckJSImfN",
)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "solaris2026")

data_lock = threading.Lock()
applications_lock = threading.Lock()

VALID_STAFF_ROLES = {
    "Java / Kotlin Developer",
    "Builder",
    "Support Staff / Moderator",
    "System Administrator",
    "2D Artist",
    "3D Modeler",
    "Game / Content Designer",
    "Animator",
    "Marketing",
    "Other",
}

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "trashmail.com", "yopmail.com",
    "tempmail.com", "throwaway.email", "sharklasers.com", "guerrillamailblock.com",
    "grr.la", "dispostable.com", "fakeinbox.com", "maildrop.cc",
    "spamgourmet.com", "spam4.me",
}

FAKE_LOCALS = {
    "test", "fake", "asdf", "qwerty", "admin123", "noreply", "null",
    "undefined", "example", "user1", "aaa", "bbb", "zzz",
}

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
REPEATED_CHARS_RE = re.compile(r'^(.)\1{3,}$')


# ── Discord ──────────────────────────────────────────────────────────────────

def _post_webhook(payload: dict):
    try:
        http_requests.post(DISCORD_WEBHOOK, json=payload, timeout=8)
    except Exception:
        pass


def send_discord(payload: dict):
    threading.Thread(target=_post_webhook, args=(payload,), daemon=True).start()


def mask_email(email: str) -> str:
    local, domain = email.split("@", 1)
    return local[0] + "***@" + domain


def notify_signup(signup: dict):
    ip_display = "hidden" if signup.get("ip_hidden") else signup.get("ip", "—")
    interests = ", ".join(signup.get("interests", [])) or "—"
    location = ", ".join(filter(None, [signup.get("city", ""), signup.get("country", "")])) or "—"
    send_discord({
        "username": "Solaris Signups",
        "embeds": [{
            "title": "🎉 New Early Access Signup!",
            "color": 3066993,
            "fields": [
                {"name": "Sign-up #", "value": str(signup["signup_number"]), "inline": True},
                {"name": "Email", "value": mask_email(signup["email"]), "inline": True},
                {"name": "Location", "value": location, "inline": True},
                {"name": "IP", "value": ip_display, "inline": True},
                {"name": "Interests", "value": interests, "inline": False},
            ],
            "timestamp": signup.get("timestamp", datetime.utcnow().isoformat()) + "Z",
        }],
    })


def notify_login(username: str, ip: str, success: bool):
    send_discord({
        "username": "Solaris Admin",
        "embeds": [{
            "title": "🔐 Admin Login Attempt",
            "color": 3066993 if success else 15158332,
            "fields": [
                {"name": "Username", "value": username or "—", "inline": True},
                {"name": "Result", "value": "✅ Success" if success else "❌ Failed", "inline": True},
                {"name": "IP", "value": ip, "inline": True},
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }],
    })


# ── Applications data ────────────────────────────────────────────────────────

def _read_applications():
    empty = {"staff": [], "testers": [], "staff_count": 0, "tester_count": 0}
    if not APPLICATIONS_FILE.exists():
        return empty
    try:
        with open(APPLICATIONS_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return empty
    data.setdefault("staff", [])
    data.setdefault("testers", [])
    data.setdefault("staff_count", len(data["staff"]))
    data.setdefault("tester_count", len(data["testers"]))
    return data


def load_applications():
    with applications_lock:
        return _read_applications()


def save_applications(data):
    tmp = Path(str(APPLICATIONS_FILE) + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(APPLICATIONS_FILE)


def notify_staff_application(app_data: dict):
    role = app_data.get("role", "Unknown")
    discord = app_data.get("general", {}).get("discord", "—")
    age = app_data.get("general", {}).get("age", "—")
    send_discord({
        "username": "Solaris Applications",
        "embeds": [{
            "title": f"📋 New Staff Application — {role}",
            "color": 6892787,
            "fields": [
                {"name": "Role", "value": role, "inline": True},
                {"name": "Discord", "value": discord, "inline": True},
                {"name": "Age", "value": age, "inline": True},
                {"name": "Application #", "value": str(app_data.get("id", "?")), "inline": True},
            ],
            "timestamp": app_data.get("timestamp", datetime.utcnow().isoformat()) + "Z",
        }],
    })


def notify_tester_application(app_data: dict):
    send_discord({
        "username": "Solaris Applications",
        "embeds": [{
            "title": "🎮 New Tester Application",
            "color": 1547855,
            "fields": [
                {"name": "IGN", "value": app_data.get("minecraft_ign", "—"), "inline": True},
                {"name": "Discord", "value": app_data.get("discord", "—"), "inline": True},
                {"name": "Age", "value": app_data.get("age", "—"), "inline": True},
                {"name": "Skill Level", "value": str(app_data.get("skill_level", "—")) + "/10", "inline": True},
                {"name": "Application #", "value": str(app_data.get("id", "?")), "inline": True},
            ],
            "timestamp": app_data.get("timestamp", datetime.utcnow().isoformat()) + "Z",
        }],
    })


# ── Data helpers ─────────────────────────────────────────────────────────────

def _read_data():
    empty = {"total_signups": 0, "signups": [], "ip_attempts": {}, "ip_signups": {}}
    if not DATA_FILE.exists():
        return empty
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return empty
    data.setdefault("total_signups", 0)
    data.setdefault("signups", [])
    data.setdefault("ip_attempts", {})
    data.setdefault("ip_signups", {})
    return data


def load_data():
    with data_lock:
        return _read_data()


def save_data(data):
    tmp = Path(str(DATA_FILE) + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(DATA_FILE)


def save_signup_txt(data):
    lines = []
    for s in data["signups"]:
        lines.append(
            f"{s['signup_number']}. {s['email']} — {s['date']} {s['time']} ({s.get('country', '')})\n"
        )
    with open(SIGNUPS_FILE, "w") as f:
        f.writelines(lines)


# ── Backups ───────────────────────────────────────────────────────────────────

def do_backup():
    BACKUPS_DIR.mkdir(exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archive = BACKUPS_DIR / f"backup_{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        if DATA_FILE.exists():
            tar.add(DATA_FILE)
        if SIGNUPS_FILE.exists():
            tar.add(SIGNUPS_FILE)


def backup_loop():
    while True:
        time.sleep(12 * 3600)
        do_backup()


threading.Thread(target=backup_loop, daemon=True).start()


# ── Validation ────────────────────────────────────────────────────────────────

def validate_email(email):
    if not EMAIL_RE.match(email):
        return False
    local, domain = email.rsplit("@", 1)
    parts = domain.split(".")
    if len(parts) < 2:
        return False
    tld = parts[-1].lower()
    second_level = parts[-2].lower()
    if not (2 <= len(tld) <= 10):
        return False
    if tld == second_level:
        return False
    if domain.lower() in DISPOSABLE_DOMAINS:
        return False
    local_lower = local.lower()
    if local_lower in FAKE_LOCALS:
        return False
    if REPEATED_CHARS_RE.match(local_lower):
        return False
    return True


# ── Blog helpers ──────────────────────────────────────────────────────────────

def process_image_tags(content):
    return re.sub(
        r'\[image:([^\]]+)\]',
        r'<figure class="post-figure"><img src="\1" alt=""></figure>',
        content
    )


def normalize_date(d):
    if isinstance(d, datetime):
        return d.date()
    return d


def get_all_posts():
    posts = []
    if not BLOG_DIR.exists():
        return posts
    for filepath in BLOG_DIR.glob("*.md"):
        post = frontmatter.load(filepath)
        post_date = post.get("date", datetime.now().date())
        post_date = normalize_date(post_date)
        posts.append({
            "slug": filepath.stem,
            "title": post.get("title", "Untitled"),
            "date": post_date,
            "author": post.get("author", "The Solaris Team"),
            "thumbnail": post.get("thumbnail", ""),
            "header_image": post.get("header_image", ""),
            "summary": post.get("summary", ""),
            "tags": post.get("tags", []),
            "is_outdated": post_date < OUTDATED_CUTOFF,
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def get_post(slug):
    filepath = BLOG_DIR / f"{slug}.md"
    if not filepath.exists():
        return None
    post = frontmatter.load(filepath)
    processed_content = process_image_tags(post.content)
    html_content = markdown.markdown(
        processed_content,
        extensions=["fenced_code", "codehilite", "tables", "toc"]
    )
    post_date = post.get("date", datetime.now().date())
    post_date = normalize_date(post_date)
    tags = post.get("tags", [])
    all_posts = get_all_posts()
    other_posts = [p for p in all_posts if p["slug"] != slug]
    if tags:
        recommended = [p for p in other_posts if set(p["tags"]) & set(tags)][:5]
        if not recommended:
            recommended = other_posts[:5]
    else:
        recommended = other_posts[:5]
    return {
        "slug": slug,
        "title": post.get("title", "Untitled"),
        "date": post_date,
        "author": post.get("author", "The Solaris Team"),
        "thumbnail": post.get("thumbnail", ""),
        "header_image": post.get("header_image", ""),
        "summary": post.get("summary", ""),
        "tags": tags,
        "content": html_content,
        "is_outdated": post_date < OUTDATED_CUTOFF,
        "latest_posts": other_posts[:5],
        "recommended_posts": recommended,
    }


# ── Public routes ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    posts = get_all_posts()[:5]
    return render_template("index.html", posts=posts)


@app.route("/blog")
def blog_listing():
    posts = get_all_posts()
    return render_template("blog/listing.html", posts=posts)


@app.route("/blog/<slug>")
def blog_post(slug):
    post = get_post(slug)
    if not post:
        abort(404)
    return render_template("blog/post.html", post=post)


@app.route("/coming-soon")
def coming_soon():
    return render_template("coming-soon.html")


@app.route("/media")
def media_page():
    return render_template("media.html")


@app.route("/roadmap")
def roadmap():
    return render_template("roadmap.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/beta")
def beta():
    return render_template("beta.html")


@app.route("/store")
def store():
    return render_template("store.html")


@app.route("/apply")
def apply_landing():
    return render_template("apply.html")


@app.route("/apply/staff", methods=["GET", "POST"])
def apply_staff():
    if request.method == "GET":
        return render_template("apply_staff.html")

    try:
        role = request.form.get("role", "").strip()
        if role not in VALID_STAFF_ROLES:
            return jsonify({"error": "invalid_role"}), 400

        discord = request.form.get("discord", "").strip()
        age = request.form.get("age", "").strip()
        microphone = request.form.get("microphone", "").strip()

        if not discord or not age or not microphone:
            return jsonify({"error": "missing_required"}), 400

        role_fields = {}
        if role == "Java / Kotlin Developer":
            role_fields["github"] = request.form.get("github", "").strip()
            role_fields["languages"] = request.form.getlist("languages")
            role_fields["experience"] = request.form.get("experience", "").strip()
            role_fields["years_coding"] = request.form.get("years_coding", "").strip()
        elif role == "Builder":
            role_fields["experience"] = request.form.get("experience", "").strip()
            role_fields["years_building"] = request.form.get("years_building", "").strip()
            role_fields["style"] = request.form.get("style", "").strip()
            role_fields["portfolio"] = request.form.get("portfolio", "").strip()
        elif role == "Support Staff / Moderator":
            role_fields["experience"] = request.form.get("experience", "").strip()
            role_fields["years_support"] = request.form.get("years_support", "").strip()
        elif role == "System Administrator":
            role_fields["experience"] = request.form.get("experience", "").strip()
            role_fields["years_sysadmin"] = request.form.get("years_sysadmin", "").strip()
        elif role == "2D Artist":
            role_fields["art_type"] = request.form.get("art_type", "").strip()
            role_fields["experience"] = request.form.get("experience", "").strip()
            role_fields["years_art"] = request.form.get("years_art", "").strip()
            role_fields["portfolio"] = request.form.get("portfolio", "").strip()
        elif role == "3D Modeler":
            role_fields["model_type"] = request.form.get("model_type", "").strip()
            role_fields["software"] = request.form.get("software", "").strip()
            role_fields["experience"] = request.form.get("experience", "").strip()
            role_fields["years_modeling"] = request.form.get("years_modeling", "").strip()
            role_fields["portfolio"] = request.form.get("portfolio", "").strip()
        elif role == "Game / Content Designer":
            role_fields["fav_aspect"] = request.form.get("fav_aspect", "").strip()
            role_fields["experience"] = request.form.get("experience", "").strip()
            role_fields["years_design"] = request.form.get("years_design", "").strip()
            role_fields["process"] = request.form.get("process", "").strip()
        elif role == "Animator":
            role_fields["anim_type"] = request.form.get("anim_type", "").strip()
            role_fields["experience"] = request.form.get("experience", "").strip()
            role_fields["years_animating"] = request.form.get("years_animating", "").strip()
        elif role == "Marketing":
            role_fields["experience"] = request.form.get("experience", "").strip()
            role_fields["years_marketing"] = request.form.get("years_marketing", "").strip()
            role_fields["best_method"] = request.form.get("best_method", "").strip()
        elif role == "Other":
            role_fields["custom_role"] = request.form.get("custom_role", "").strip()
            role_fields["experience"] = request.form.get("experience", "").strip()

        now = datetime.utcnow()
        ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()

        app_record = {
            "role": role,
            "role_fields": role_fields,
            "general": {
                "discord": discord,
                "age": age,
                "microphone": microphone,
                "socials": request.form.get("socials", "").strip(),
                "portfolio_link": request.form.get("portfolio_link", "").strip(),
                "extra": request.form.get("extra", "").strip(),
            },
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "ip": ip,
            "status": "pending",
        }

        with applications_lock:
            data = _read_applications()
            app_record["id"] = len(data["staff"]) + 1
            data["staff"].append(app_record)
            data["staff_count"] = len(data["staff"])
            save_applications(data)

        notify_staff_application(app_record)
        return jsonify({"success": True, "id": app_record["id"]})

    except Exception as e:
        app.logger.error("apply_staff error: %s", e, exc_info=True)
        return jsonify({"error": "server_error"}), 500


@app.route("/apply/tester", methods=["GET", "POST"])
def apply_tester():
    if request.method == "GET":
        return render_template("apply_tester.html")

    try:
        email = request.form.get("email", "").strip().lower()
        if not validate_email(email):
            return jsonify({"error": "invalid_email"}), 400

        rules_agreed = request.form.get("rules_agreed", "")
        blacklist_agreed = request.form.get("blacklist_agreed", "")
        owns_java = request.form.get("owns_java", "")
        feedback_ok = request.form.get("feedback_ok", "")

        if rules_agreed != "yes" or blacklist_agreed != "yes":
            return jsonify({"error": "must_agree_rules"}), 400
        if owns_java != "yes":
            return jsonify({"error": "must_own_java"}), 400
        if feedback_ok != "yes":
            return jsonify({"error": "must_accept_feedback"}), 400

        minecraft_ign = request.form.get("minecraft_ign", "").strip()
        discord = request.form.get("discord", "").strip()
        age = request.form.get("age", "").strip()
        pronouns = request.form.get("pronouns", "").strip()

        if not all([minecraft_ign, discord, age, pronouns]):
            return jsonify({"error": "missing_required"}), 400

        try:
            skill_level = int(request.form.get("skill_level", "0"))
            if not (1 <= skill_level <= 10):
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"error": "invalid_skill_level"}), 400

        now = datetime.utcnow()
        ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()

        app_record = {
            "email": email,
            "minecraft_ign": minecraft_ign,
            "discord": discord,
            "age": age,
            "pronouns": pronouns,
            "owns_java": owns_java,
            "tested_before": request.form.get("tested_before", "no"),
            "rules_agreed": rules_agreed,
            "feedback_ok": feedback_ok,
            "blacklist_agreed": blacklist_agreed,
            "skill_level": skill_level,
            "prior_testing": request.form.get("prior_testing", "").strip(),
            "other_experience": request.form.get("other_experience", "").strip(),
            "opinion": request.form.get("opinion", "").strip(),
            "improvements": request.form.get("improvements", "").strip(),
            "extra": request.form.get("extra", "").strip(),
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "ip": ip,
            "status": "pending",
        }

        with applications_lock:
            data = _read_applications()
            app_record["id"] = len(data["testers"]) + 1
            data["testers"].append(app_record)
            data["tester_count"] = len(data["testers"])
            save_applications(data)

        notify_tester_application(app_record)
        return jsonify({"success": True, "id": app_record["id"]})

    except Exception as e:
        app.logger.error("apply_tester error: %s", e, exc_info=True)
        return jsonify({"error": "server_error"}), 500


@app.route("/beta-signup", methods=["POST"])
def beta_signup():
    try:
        turnstile_token = request.form.get("cf-turnstile-response", "")
        try:
            ts_resp = http_requests.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={"secret": "0x4AAAAAADP2YAS46FJKPtpd62RtX2SP1vs", "response": turnstile_token},
                timeout=10,
            )
            ts_data = ts_resp.json()
        except Exception:
            return jsonify({"error": "turnstile_failed"}), 400

        if not ts_data.get("success"):
            return jsonify({"error": "turnstile_failed"}), 400

        ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
        email = request.form.get("email", "").strip().lower()

        if not validate_email(email):
            return jsonify({"error": "invalid_email"}), 400

        interests = request.form.getlist("excitement")
        ip_consent = request.form.get("ip_consent", "false")

        try:
            geo_resp = http_requests.get(
                f"http://ip-api.com/json/{ip}?fields=country,countryCode,city,regionName",
                timeout=5,
            )
            geo = geo_resp.json()
        except Exception:
            geo = {}

        with data_lock:
            data = _read_data()

            if data["ip_attempts"].get(ip, 0) >= 3:
                return jsonify({"error": "too_many_attempts"}), 429

            if email in {s["email"].lower() for s in data["signups"]}:
                return jsonify({"error": "already_signed_up"}), 409

            total = data["total_signups"] + 1
            now = datetime.utcnow()
            signup = {
                "id": total,
                "signup_number": total,
                "email": email,
                "timestamp": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "ip": ip if ip_consent == "true" else "hidden",
                "ip_hidden": ip_consent != "true",
                "country": geo.get("country", ""),
                "country_code": geo.get("countryCode", ""),
                "city": geo.get("city", ""),
                "region": geo.get("regionName", ""),
                "interests": interests,
            }

            data["total_signups"] = total
            data["signups"].append(signup)
            data["ip_attempts"][ip] = data["ip_attempts"].get(ip, 0) + 1
            data["ip_signups"][ip] = email

            save_data(data)
            try:
                save_signup_txt(data)
            except Exception as txt_err:
                app.logger.warning("save_signup_txt failed: %s", txt_err)

        notify_signup(signup)
        return jsonify({"success": True, "number": total})

    except Exception as e:
        app.logger.error("beta_signup error: %s", e, exc_info=True)
        return jsonify({"error": "server_error"}), 500


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()

        valid_user = secrets.compare_digest(username, ADMIN_USERNAME)
        valid_pass = secrets.compare_digest(password, ADMIN_PASSWORD)
        success = valid_user and valid_pass

        notify_login(username, ip, success)

        if success:
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("admin_login.html", error="Invalid credentials.")

    if not session.get("admin"):
        return render_template("admin_login.html", error=None)

    data = load_data()
    signups = list(reversed(data["signups"]))
    country_breakdown = {}
    for s in data["signups"]:
        c = s.get("country", "") or "Unknown"
        country_breakdown[c] = country_breakdown.get(c, 0) + 1

    apps = load_applications()
    staff_apps = list(reversed(apps["staff"]))
    tester_apps = list(reversed(apps["testers"]))

    return render_template(
        "admin.html",
        total=data["total_signups"],
        signups=signups,
        country_breakdown=country_breakdown,
        ip_attempts=data["ip_attempts"],
        staff_apps=staff_apps,
        tester_apps=tester_apps,
    )


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin"))


@app.route("/admin/applications/status", methods=["POST"])
def admin_update_application_status():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401

    app_type = request.json.get("type")
    app_id   = request.json.get("id")
    status   = request.json.get("status")

    if app_type not in ("staff", "tester") or status not in ("pending", "accepted", "rejected"):
        return jsonify({"error": "invalid_params"}), 400

    collection_key = "staff" if app_type == "staff" else "testers"

    with applications_lock:
        data = _read_applications()
        collection = data.get(collection_key, [])
        for entry in collection:
            if entry.get("id") == app_id:
                entry["status"] = status
                break
        else:
            return jsonify({"error": "not_found"}), 404
        save_applications(data)

    return jsonify({"ok": True, "status": status})


if __name__ == "__main__":
    app.run(debug=True, port=7060, host="127.0.0.1")
