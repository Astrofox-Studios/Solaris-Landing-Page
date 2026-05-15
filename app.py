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

DISCORD_WEBHOOK = os.environ.get(
    "DISCORD_WEBHOOK",
    "https://discord.com/api/webhooks/1504789105714925661/e4-Pq_eF89ksaEQs2zwWx01rfKQbd70cwyFxxhIUZQN1OTIxXRoVryEHLUy5ckJSImfN",
)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "solaris2026")

data_lock = threading.Lock()

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


# ── Data helpers ─────────────────────────────────────────────────────────────

def _read_data():
    if not DATA_FILE.exists():
        return {"total_signups": 0, "signups": [], "ip_attempts": {}, "ip_signups": {}}
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
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


@app.route("/beta-signup", methods=["POST"])
def beta_signup():
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
        save_signup_txt(data)

    notify_signup(signup)
    return jsonify({"success": True, "number": total})


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

    return render_template(
        "admin.html",
        total=data["total_signups"],
        signups=signups,
        country_breakdown=country_breakdown,
        ip_attempts=data["ip_attempts"],
    )


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True, port=7060, host="127.0.0.1")
