from flask import Flask, render_template, abort
from pathlib import Path
from datetime import datetime, date
import frontmatter
import markdown
import re

app = Flask(__name__)
BLOG_DIR = Path("content/blog")
OUTDATED_CUTOFF = date(2026, 1, 1)


def process_image_tags(content):
    """Convert [image:path] to HTML figure/img tags."""
    return re.sub(
        r'\[image:([^\]]+)\]',
        r'<figure class="post-figure"><img src="\1" alt=""></figure>',
        content
    )


def normalize_date(d):
    """Ensure we always have a date object for comparison."""
    if isinstance(d, datetime):
        return d.date()
    return d


def get_all_posts():
    """Read all markdown blog posts, parse frontmatter, sort by date descending."""
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
    """Read a single blog post by slug, return metadata + rendered HTML."""
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

    # Recommended: posts sharing at least one tag; fall back to latest
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


if __name__ == "__main__":
    app.run(debug=True, port=7060, host="127.0.0.1")
