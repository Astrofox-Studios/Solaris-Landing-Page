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
try:
    import bcrypt as _bcrypt
    import bot as auth_bot
    _AUTH_BOT_OK = True
except ImportError:
    _bcrypt = None
    auth_bot = None
    _AUTH_BOT_OK = False

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

BLOG_DIR = Path("content/blog")
OUTDATED_CUTOFF = date(2026, 1, 1)
DATA_FILE = Path("data.json")
SIGNUPS_FILE = Path("signups.txt")
BACKUPS_DIR = Path("backups")
APPLICATIONS_FILE = Path("applications.json")

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
ADMIN_USERNAME  = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD  = os.environ.get("ADMIN_PASSWORD", "")
BOT_TOKEN       = os.environ.get("DISCORD_BOT_TOKEN", "")
ADMIN_AUTH_FILE = Path("admin_auth.json")

COUNTDOWN_TARGET  = os.environ.get("COUNTDOWN_TARGET", "")    # ISO datetime, e.g. "2026-06-27T12:00:00"
COUNTDOWN_LABEL   = os.environ.get("COUNTDOWN_LABEL", "Early Access")
COUNTDOWN_VISIBLE = os.environ.get("COUNTDOWN_VISIBLE", "false").lower() == "true"

data_lock = threading.Lock()
applications_lock = threading.Lock()

VISITS_FILE = Path("visits.json")
visits_lock  = threading.Lock()
MAX_VISITS   = 10_000

_CONTINENT_MAP: dict[str, str] = {
    # Africa
    "DZ":"Africa","AO":"Africa","BJ":"Africa","BW":"Africa","BF":"Africa","BI":"Africa","CV":"Africa",
    "CM":"Africa","CF":"Africa","TD":"Africa","KM":"Africa","CG":"Africa","CD":"Africa","CI":"Africa",
    "DJ":"Africa","EG":"Africa","GQ":"Africa","ER":"Africa","SZ":"Africa","ET":"Africa","GA":"Africa",
    "GM":"Africa","GH":"Africa","GN":"Africa","GW":"Africa","KE":"Africa","LS":"Africa","LR":"Africa",
    "LY":"Africa","MG":"Africa","MW":"Africa","ML":"Africa","MR":"Africa","MU":"Africa","YT":"Africa",
    "MA":"Africa","MZ":"Africa","NA":"Africa","NE":"Africa","NG":"Africa","RE":"Africa","RW":"Africa",
    "SH":"Africa","ST":"Africa","SN":"Africa","SC":"Africa","SL":"Africa","SO":"Africa","ZA":"Africa",
    "SS":"Africa","SD":"Africa","TZ":"Africa","TG":"Africa","TN":"Africa","UG":"Africa","EH":"Africa",
    "ZM":"Africa","ZW":"Africa",
    # Antarctica
    "AQ":"Antarctica",
    # Asia
    "AF":"Asia","AM":"Asia","AZ":"Asia","BH":"Asia","BD":"Asia","BT":"Asia","BN":"Asia","KH":"Asia",
    "CN":"Asia","CY":"Asia","GE":"Asia","HK":"Asia","IN":"Asia","ID":"Asia","IR":"Asia","IQ":"Asia",
    "IL":"Asia","JP":"Asia","JO":"Asia","KZ":"Asia","KW":"Asia","KG":"Asia","LA":"Asia","LB":"Asia",
    "MO":"Asia","MY":"Asia","MV":"Asia","MN":"Asia","MM":"Asia","NP":"Asia","KP":"Asia","OM":"Asia",
    "PK":"Asia","PS":"Asia","PH":"Asia","QA":"Asia","SA":"Asia","SG":"Asia","KR":"Asia","LK":"Asia",
    "SY":"Asia","TW":"Asia","TJ":"Asia","TH":"Asia","TL":"Asia","TR":"Asia","TM":"Asia","AE":"Asia",
    "UZ":"Asia","VN":"Asia","YE":"Asia",
    # Europe
    "AL":"Europe","AD":"Europe","AT":"Europe","BY":"Europe","BE":"Europe","BA":"Europe","BG":"Europe",
    "HR":"Europe","CY":"Europe","CZ":"Europe","DK":"Europe","EE":"Europe","FI":"Europe","FR":"Europe",
    "DE":"Europe","GI":"Europe","GR":"Europe","HU":"Europe","IS":"Europe","IE":"Europe","IT":"Europe",
    "XK":"Europe","LV":"Europe","LI":"Europe","LT":"Europe","LU":"Europe","MT":"Europe","MD":"Europe",
    "MC":"Europe","ME":"Europe","NL":"Europe","MK":"Europe","NO":"Europe","PL":"Europe","PT":"Europe",
    "RO":"Europe","RU":"Europe","SM":"Europe","RS":"Europe","SK":"Europe","SI":"Europe","ES":"Europe",
    "SE":"Europe","CH":"Europe","UA":"Europe","GB":"Europe","VA":"Europe",
    # North America
    "AG":"North America","BS":"North America","BB":"North America","BZ":"North America","CA":"North America",
    "CR":"North America","CU":"North America","DM":"North America","DO":"North America","SV":"North America",
    "GD":"North America","GT":"North America","HT":"North America","HN":"North America","JM":"North America",
    "MX":"North America","NI":"North America","PA":"North America","KN":"North America","LC":"North America",
    "VC":"North America","TT":"North America","US":"North America",
    "PR":"North America","VI":"North America","GP":"North America","MQ":"North America",
    # Oceania
    "AU":"Oceania","FJ":"Oceania","KI":"Oceania","MH":"Oceania","FM":"Oceania","NR":"Oceania","NZ":"Oceania",
    "PW":"Oceania","PG":"Oceania","WS":"Oceania","SB":"Oceania","TO":"Oceania","TV":"Oceania","VU":"Oceania",
    "CK":"Oceania","GU":"Oceania","PF":"Oceania","NC":"Oceania",
    # South America
    "AR":"South America","BO":"South America","BR":"South America","CL":"South America","CO":"South America",
    "EC":"South America","FK":"South America","GF":"South America","GY":"South America","PY":"South America",
    "PE":"South America","SR":"South America","UY":"South America","VE":"South America",
}

def _code_to_continent(code: str) -> str:
    return _CONTINENT_MAP.get((code or "").upper(), "Other")

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


# ── Visitor tracking ─────────────────────────────────────────────────────────

def _read_visits():
    empty = {"total_visits": 0, "visits": [], "ip_geo_cache": {}}
    if not VISITS_FILE.exists():
        return empty
    try:
        with open(VISITS_FILE, "r") as f:
            d = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return empty
    d.setdefault("total_visits", 0)
    d.setdefault("visits", [])
    d.setdefault("ip_geo_cache", {})
    return d


def _save_visits(data):
    tmp = Path(str(VISITS_FILE) + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(VISITS_FILE)


def _geo_and_update_visit(ip: str, timestamp: str):
    try:
        geo_resp = http_requests.get(
            f"http://ip-api.com/json/{ip}?fields=country,countryCode,city",
            timeout=5,
        )
        geo = geo_resp.json()
    except Exception:
        geo = {}
    geo_entry = {
        "country": geo.get("country", ""),
        "country_code": geo.get("countryCode", ""),
        "city": geo.get("city", ""),
    }
    with visits_lock:
        data = _read_visits()
        data["ip_geo_cache"][ip] = geo_entry
        for v in reversed(data["visits"]):
            if v.get("ip") == ip and v.get("timestamp") == timestamp:
                v.update(geo_entry)
                break
        _save_visits(data)


_VISIT_SKIP_PREFIXES = ("/admin", "/static", "/favicon", "/beta-signup", "/apply")

def record_visit():
    if request.method != "GET":
        return
    path = request.path
    if any(path.startswith(p) for p in _VISIT_SKIP_PREFIXES):
        return
    ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
    now = datetime.utcnow()
    timestamp = now.isoformat()
    date_str  = now.strftime("%Y-%m-%d")
    needs_geo = False
    try:
        with visits_lock:
            data = _read_visits()
            geo_cached = data["ip_geo_cache"].get(ip)
            visit = {
                "timestamp": timestamp,
                "date": date_str,
                "ip": ip,
                "path": path,
                "country":      (geo_cached or {}).get("country", ""),
                "country_code": (geo_cached or {}).get("country_code", ""),
                "city":         (geo_cached or {}).get("city", ""),
            }
            data["visits"].append(visit)
            if len(data["visits"]) > MAX_VISITS:
                data["visits"] = data["visits"][-MAX_VISITS:]
            data["total_visits"] = len(data["visits"])
            needs_geo = geo_cached is None
            _save_visits(data)
    except Exception:
        pass
    if needs_geo:
        threading.Thread(target=_geo_and_update_visit, args=(ip, timestamp), daemon=True).start()


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

# ── Admin auth helpers ────────────────────────────────────────────────────────

def _load_auth_config() -> dict:
    if ADMIN_AUTH_FILE.exists():
        try:
            with open(ADMIN_AUTH_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_auth_config(data: dict):
    tmp = Path(str(ADMIN_AUTH_FILE) + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(ADMIN_AUTH_FILE)


def check_admin_password(password: str) -> bool:
    # Always reject empty submissions
    if not password:
        return False
    stored = _load_auth_config().get("password_hash", "")
    if stored:
        # Hash exists — use bcrypt (fast path for all logins after first)
        return _bcrypt and _bcrypt.checkpw(password.encode(), stored.encode())
    # No hash yet: compare against ADMIN_PASSWORD from .env and auto-migrate
    env_pw = ADMIN_PASSWORD
    if not env_pw:
        return False
    if secrets.compare_digest(password, env_pw):
        if _bcrypt:
            new_hash = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(12)).decode()
            _save_auth_config({"password_hash": new_hash})
        return True
    return False


def update_admin_password(new_password: str):
    if not _bcrypt:
        return
    new_hash = _bcrypt.hashpw(new_password.encode(), _bcrypt.gensalt(12)).decode()
    _save_auth_config({"password_hash": new_hash})


# ── Login rate limiter ────────────────────────────────────────────────────────

_login_attempts: dict = {}
_login_ratelimit_lock = threading.Lock()
_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_WINDOW = 900  # 15 minutes


def _login_allowed(ip: str) -> bool:
    now = time.time()
    with _login_ratelimit_lock:
        recent = [t for t in _login_attempts.get(ip, []) if now - t < _LOGIN_WINDOW]
        _login_attempts[ip] = recent
        return len(recent) < _MAX_LOGIN_ATTEMPTS


def _record_login_fail(ip: str):
    now = time.time()
    with _login_ratelimit_lock:
        recent = [t for t in _login_attempts.get(ip, []) if now - t < _LOGIN_WINDOW]
        recent.append(now)
        _login_attempts[ip] = recent


# ── Start Discord auth bot ────────────────────────────────────────────────────

if _AUTH_BOT_OK and BOT_TOKEN:
    auth_bot.start(BOT_TOKEN)
elif not BOT_TOKEN:
    import logging as _logging
    _logging.getLogger(__name__).warning("DISCORD_BOT_TOKEN not set — admin login will be blocked")


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


# ── Visitor hook ─────────────────────────────────────────────────────────────

@app.before_request
def _track():
    record_visit()


# ── Public routes ─────────────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    formatted = ""
    if COUNTDOWN_TARGET:
        try:
            dt = datetime.fromisoformat(COUNTDOWN_TARGET.rstrip('Z'))
            date_str = dt.strftime("%B %d, %Y")
            hour12 = dt.hour % 12 or 12
            ampm = "PM" if dt.hour >= 12 else "AM"
            minute = f":{dt.minute:02d}" if dt.minute else ""
            tz_map = {-5: "EST", -4: "EST", 0: "UTC", 1: "BST"}
            tz_label = ""
            if dt.utcoffset() is not None:
                tz_label = " " + tz_map.get(int(dt.utcoffset().total_seconds() / 3600), "")
            formatted = f"{date_str} at {hour12}{minute} {ampm}{tz_label}".strip()
        except (ValueError, AttributeError):
            formatted = COUNTDOWN_TARGET
    return dict(
        countdown_visible=COUNTDOWN_VISIBLE,
        countdown_target=COUNTDOWN_TARGET,
        countdown_label=COUNTDOWN_LABEL,
        countdown_target_formatted=formatted,
    )


@app.route("/")
def index():
    posts = get_all_posts()[:5]
    return render_template("index.html", posts=posts)


@app.route("/countdown")
def countdown_page():
    return render_template("countdown.html")


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


@app.route("/earlyaccess")
def early_access():
    return render_template("beta.html")


@app.route("/beta")
def beta():
    return redirect(url_for("early_access"), 301)


@app.route("/discord")
def discord_redirect():
    return redirect("https://discord.gg/8nnn25B6pU", 301)


@app.route("/api/signup-count")
def api_signup_count():
    data = load_data()
    return jsonify({"count": data["total_signups"]})


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

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return render_template("admin_login.html")

    from datetime import timedelta

    data = load_data()
    signups = list(reversed(data["signups"]))

    country_breakdown: dict = {}
    interests_breakdown: dict = {}
    for s in data["signups"]:
        c = s.get("country") or "Unknown"
        country_breakdown[c] = country_breakdown.get(c, 0) + 1
        for interest in s.get("interests", []):
            interests_breakdown[interest] = interests_breakdown.get(interest, 0) + 1

    today_date = datetime.utcnow().date()
    date_range = [(today_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]

    signup_by_date: dict = {}
    for s in data["signups"]:
        signup_by_date[s["date"]] = signup_by_date.get(s["date"], 0) + 1
    signup_daily_counts = {d: signup_by_date.get(d, 0) for d in date_range}

    # Signup continent + top cities
    signup_continent_breakdown: dict = {}
    signup_city_counts: dict = {}
    for s in data["signups"]:
        cont = _code_to_continent(s.get("country_code", ""))
        signup_continent_breakdown[cont] = signup_continent_breakdown.get(cont, 0) + 1
        city = s.get("city") or ""
        if city:
            signup_city_counts[city] = signup_city_counts.get(city, 0) + 1
    signup_top_cities = dict(sorted(signup_city_counts.items(), key=lambda x: x[1], reverse=True)[:8])

    # Visitor stats
    with visits_lock:
        vdata = _read_visits()
    all_visits = vdata["visits"]
    today_str   = today_date.strftime("%Y-%m-%d")
    today_visits = sum(1 for v in all_visits if v.get("date") == today_str)
    unique_ips   = len({v.get("ip") for v in all_visits})

    visit_country_breakdown: dict = {}
    visit_continent_breakdown: dict = {}
    visit_page_counts: dict = {}
    visit_hourly_counts: dict = {str(h).zfill(2): 0 for h in range(24)}
    visit_city_counts: dict = {}
    for v in all_visits:
        c = v.get("country") or "Unknown"
        visit_country_breakdown[c] = visit_country_breakdown.get(c, 0) + 1
        cont = _code_to_continent(v.get("country_code", ""))
        visit_continent_breakdown[cont] = visit_continent_breakdown.get(cont, 0) + 1
        page = v.get("path", "/")
        visit_page_counts[page] = visit_page_counts.get(page, 0) + 1
        ts = v.get("timestamp", "")
        if len(ts) >= 13:
            hour = ts[11:13]
            if hour in visit_hourly_counts:
                visit_hourly_counts[hour] += 1
        city = v.get("city") or ""
        if city:
            visit_city_counts[city] = visit_city_counts.get(city, 0) + 1

    visit_top_pages = dict(sorted(visit_page_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    visit_top_cities = dict(sorted(visit_city_counts.items(), key=lambda x: x[1], reverse=True)[:8])

    visit_by_date: dict = {}
    for v in all_visits:
        visit_by_date[v["date"]] = visit_by_date.get(v["date"], 0) + 1
    visit_daily_counts = {d: visit_by_date.get(d, 0) for d in date_range}

    recent_visits = list(reversed(all_visits))[:100]

    # Conversion rate
    conversion_rate = round(data["total_signups"] / unique_ips * 100, 1) if unique_ips else 0.0

    apps = load_applications()
    staff_apps  = list(reversed(apps["staff"]))
    tester_apps = list(reversed(apps["testers"]))

    # Staff role breakdown
    staff_role_breakdown: dict = {}
    for a in apps["staff"]:
        r = a.get("role", "Unknown")
        staff_role_breakdown[r] = staff_role_breakdown.get(r, 0) + 1
    staff_role_breakdown = dict(sorted(staff_role_breakdown.items(), key=lambda x: x[1], reverse=True))

    # Tester skill level distribution
    tester_skill_breakdown: dict = {str(i): 0 for i in range(1, 11)}
    for a in apps["testers"]:
        lvl = str(a.get("skill_level", ""))
        if lvl in tester_skill_breakdown:
            tester_skill_breakdown[lvl] += 1

    return render_template(
        "admin.html",
        total=data["total_signups"],
        signups=signups,
        country_breakdown=country_breakdown,
        interests_breakdown=interests_breakdown,
        signup_daily_counts=signup_daily_counts,
        signup_continent_breakdown=signup_continent_breakdown,
        signup_top_cities=signup_top_cities,
        ip_attempts=data["ip_attempts"],
        staff_apps=staff_apps,
        tester_apps=tester_apps,
        staff_role_breakdown=staff_role_breakdown,
        tester_skill_breakdown=tester_skill_breakdown,
        total_visits=vdata["total_visits"],
        unique_ips=unique_ips,
        today_visits=today_visits,
        conversion_rate=conversion_rate,
        visit_country_breakdown=visit_country_breakdown,
        visit_continent_breakdown=visit_continent_breakdown,
        visit_top_pages=visit_top_pages,
        visit_top_cities=visit_top_cities,
        visit_hourly_counts=visit_hourly_counts,
        visit_daily_counts=visit_daily_counts,
        recent_visits=recent_visits,
    )


@app.route("/admin/login", methods=["POST"])
def admin_login():
    if not _AUTH_BOT_OK or not BOT_TOKEN:
        return jsonify({"error": "Discord 2FA not configured on the server."}), 503

    ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()

    if not _login_allowed(ip):
        return jsonify({"error": "Too many attempts. Try again in 15 minutes."}), 429

    username = request.form.get("username", "")
    password = request.form.get("password", "")

    valid_user = secrets.compare_digest(username, ADMIN_USERNAME)
    valid_pass = check_admin_password(password) if valid_user else False

    if not (valid_user and valid_pass):
        _record_login_fail(ip)
        notify_login(username, ip, False)
        return jsonify({"error": "Invalid credentials."}), 401

    req_id = secrets.token_urlsafe(32)
    ua = request.headers.get("User-Agent", "")
    auth_bot.create_request(req_id, ip, ua)
    return jsonify({"pending": True, "request_id": req_id})


@app.route("/admin/login/check")
def admin_login_check():
    req_id = request.args.get("id", "")
    if not req_id or not _AUTH_BOT_OK:
        return jsonify({"status": "expired"})

    status = auth_bot.get_status(req_id)

    if status == "approved" and auth_bot.consume(req_id):
        ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
        session["admin"] = True
        notify_login(ADMIN_USERNAME, ip, True)
        return jsonify({"status": "approved"})

    return jsonify({"status": status})


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin"))


@app.route("/admin/change-password", methods=["POST"])
def admin_change_password():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401

    body        = request.json or {}
    current_pw  = body.get("current_password", "")
    new_pw      = body.get("new_password", "")

    if not check_admin_password(current_pw):
        return jsonify({"error": "Current password is incorrect."}), 403
    if len(new_pw) < 12:
        return jsonify({"error": "New password must be at least 12 characters."}), 400

    update_admin_password(new_pw)
    return jsonify({"ok": True})


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


@app.route("/admin/signups/remove", methods=["POST"])
def admin_remove_signup():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401
    signup_id = (request.json or {}).get("id")
    if signup_id is None:
        return jsonify({"error": "missing id"}), 400
    with data_lock:
        d = _read_data()
        before = len(d["signups"])
        d["signups"] = [s for s in d["signups"] if s.get("id") != signup_id]
        if len(d["signups"]) == before:
            return jsonify({"error": "not_found"}), 404
        d["total_signups"] = len(d["signups"])
        save_data(d)
    return jsonify({"ok": True})


@app.route("/admin/signups/add", methods=["POST"])
def admin_add_signup():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401
    body  = request.json or {}
    email = body.get("email", "").strip().lower()
    if not email or not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email address"}), 400
    with data_lock:
        d = _read_data()
        if email in {s["email"].lower() for s in d["signups"]}:
            return jsonify({"error": "Email already exists"}), 409
        new_id  = max((s.get("id", 0) for s in d["signups"]), default=0) + 1
        new_num = max((s.get("signup_number", 0) for s in d["signups"]), default=0) + 1
        now = datetime.utcnow()
        signup = {
            "id": new_id,
            "signup_number": new_num,
            "email": email,
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "ip": "admin-added",
            "ip_hidden": False,
            "country": "",
            "country_code": "",
            "city": "",
            "region": "",
            "interests": body.get("interests", []),
        }
        d["signups"].append(signup)
        d["total_signups"] = len(d["signups"])
        save_data(d)
    return jsonify({"ok": True, "signup": signup})


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy.html")


@app.route("/branding")
def branding():
    return render_template("branding.html")


if __name__ == "__main__":
    app.run(debug=True, port=7060, host="127.0.0.1")
