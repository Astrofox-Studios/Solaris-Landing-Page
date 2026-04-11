from flask import Flask, render_template, abort
from pathlib import Path
from datetime import datetime
import frontmatter
import markdown

app = Flask(__name__)
BLOG_DIR = Path("content/blog")


def get_all_posts():
    """Read all markdown blog posts, parse frontmatter, sort by date descending."""
    posts = []
    if not BLOG_DIR.exists():
        return posts

    for filepath in BLOG_DIR.glob("*.md"):
        post = frontmatter.load(filepath)
        posts.append({
            "slug": filepath.stem,
            "title": post.get("title", "Untitled"),
            "date": post.get("date", datetime.now().date()),
            "author": post.get("author", "The Solaris Team"),
            "thumbnail": post.get("thumbnail", ""),
            "summary": post.get("summary", ""),
            "tags": post.get("tags", []),
        })

    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def get_post(slug):
    """Read a single blog post by slug, return metadata + rendered HTML."""
    filepath = BLOG_DIR / f"{slug}.md"
    if not filepath.exists():
        return None

    post = frontmatter.load(filepath)
    html_content = markdown.markdown(
        post.content,
        extensions=["fenced_code", "codehilite", "tables", "toc"]
    )

    return {
        "slug": slug,
        "title": post.get("title", "Untitled"),
        "date": post.get("date", datetime.now().date()),
        "author": post.get("author", "The Solaris Team"),
        "thumbnail": post.get("thumbnail", ""),
        "summary": post.get("summary", ""),
        "tags": post.get("tags", []),
        "content": html_content,
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


@app.route("/media")
def media_page():
    return render_template("media.html")


@app.route("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=True)
