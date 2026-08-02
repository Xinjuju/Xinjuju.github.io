from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX_FILE = ROOT / "index.html"
NOTES_FILE = ROOT / "notes.html"
PAINTINGS_FILE = ROOT / "paintings.html"
PHOTOS_FILE = ROOT / "photos.html"
POSTS_DIR = ROOT / "posts"
REMOVED_POSTS = [
    POSTS_DIR / "a-place-to-keep.html",
    POSTS_DIR / "four-pm-light.html",
    POSTS_DIR / "june-sketchbook.html",
    POSTS_DIR / "painting-uncertainty.html",
]


def load_issue() -> dict:
    event_path = os.environ["GITHUB_EVENT_PATH"]
    with open(event_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["issue"]


def parse_sections(body: str) -> dict[str, str]:
    pattern = re.compile(r"^###\s+(.+?)\n(.*?)(?=^###\s+|\Z)", re.M | re.S)
    sections: dict[str, str] = {}
    for heading, content in pattern.findall(body):
        cleaned = content.strip()
        if cleaned == "_No response_":
            cleaned = ""
        sections[heading.strip()] = cleaned
    return sections


def extract_image_url(text: str) -> str:
    markdown_image = re.search(r"!\[[^\]]*\]\((https?://[^)\s]+)\)", text)
    if markdown_image:
        return markdown_image.group(1)

    plain_url = re.search(r"(https?://\S+)", text)
    if plain_url:
        return plain_url.group(1).rstrip(")")

    return ""


def slugify(value: str) -> str:
    slug = re.sub(r"\s+", "-", value.strip().lower())
    slug = re.sub(r"[^0-9a-z\u4e00-\u9fff-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "note"


def replace_removed_post(path: Path) -> None:
    path.write_text(
        """<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="refresh" content="0; url=../notes.html" />
    <title>文章已移除</title>
  </head>
  <body>
    <p>这篇文章已移除，正在返回随记页。</p>
  </body>
</html>
""",
        encoding="utf-8",
    )


def ensure_removed_posts() -> None:
    for path in REMOVED_POSTS:
        replace_removed_post(path)


def insert_before_marker(path: Path, marker: str, snippet: str) -> None:
    content = path.read_text(encoding="utf-8")
    end_marker = f"<!-- {marker}:end -->"
    if snippet.strip() in content:
        return
    content = content.replace(end_marker, f"{snippet}\n            {end_marker}")
    path.write_text(content, encoding="utf-8")


def remove_placeholder(path: Path, placeholder: str) -> None:
    content = path.read_text(encoding="utf-8")
    if placeholder not in content:
        return
    path.write_text(content.replace(placeholder, ""), encoding="utf-8")


def render_painting_card(title: str, image_url: str, description: str) -> str:
    safe_title = html.escape(title)
    safe_image = html.escape(image_url, quote=True)
    safe_description = html.escape(description, quote=True)
    return f"""<figure class="gallery-card">
              <button
                class="gallery-button"
                type="button"
                data-description="{safe_description}"
              >
                <img src="{safe_image}" alt="{safe_title}" />
              </button>
              <figcaption>{safe_title}</figcaption>
            </figure>"""


def render_photo_card(title: str, image_url: str, description: str) -> str:
    safe_title = html.escape(title)
    safe_image = html.escape(image_url, quote=True)
    safe_description = html.escape(description)
    return f"""<article class="media-card">
              <a href="{safe_image}" class="media-card-link" target="_blank" rel="noreferrer">
                <img src="{safe_image}" alt="{safe_title}" class="media-card-image" />
                <div class="media-card-copy">
                  <strong>{safe_title}</strong>
                  <p>{safe_description}</p>
                </div>
              </a>
            </article>"""


def render_note_card(title: str, href: str) -> str:
    safe_title = html.escape(title)
    safe_href = html.escape(href, quote=True)
    return f"""<article class="article-card">
              <a href="{safe_href}" class="card-link">
                <h3>{safe_title}</h3>
              </a>
            </article>"""


def render_note_page(title: str, date: str, body: str) -> str:
    safe_title = html.escape(title)
    safe_date = html.escape(date)
    paragraphs = [segment.strip() for segment in re.split(r"\n\s*\n", body) if segment.strip()]
    paragraph_html = "\n".join(
        f"            <p>{html.escape(paragraph).replace(chr(10), '<br />')}</p>"
        for paragraph in paragraphs
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{safe_title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Crimson+Text:wght@400;600&family=Noto+Serif+SC:wght@400;500;600&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="../styles.css" />
  </head>
  <body>
    <div class="layout">
      <aside class="sidebar">
        <div class="profile">
          <p class="site-mark">JuJube Notes</p>
        </div>
        <nav class="category-nav" aria-label="返回首页">
          <a href="../index.html">回到首页</a>
        </nav>
      </aside>

      <main class="main-content post-page">
        <header class="page-header">
          <p class="page-kicker">随记</p>
          <p class="page-note">{safe_date}</p>
        </header>

        <article class="post-group">
          <div class="group-heading">
            <h2>{safe_title}</h2>
          </div>
          <div class="post-body">
{paragraph_html}
          </div>
        </article>
      </main>
    </div>
  </body>
</html>
"""


def write_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with open(output, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def main() -> None:
    issue = load_issue()
    labels = {item["name"] for item in issue["labels"]}
    sections = parse_sections(issue.get("body", ""))

    ensure_removed_posts()

    changed = False
    commit_message = f"Publish content from issue #{issue['number']}"
    published_url = ""

    photo_placeholder = """<article class="media-card media-card-empty">
              <p>照片会放在这里。</p>
            </article>
            """

    if "painting" in labels:
        title = sections["标题"]
        image_url = extract_image_url(sections.get("图片", ""))
        description = sections["解说"]
        if not image_url:
            raise ValueError("未找到图片地址。请把本地图片直接拖进“图片”一栏后再提交。")
        snippet = render_painting_card(title, image_url, description)
        insert_before_marker(INDEX_FILE, "paintings", snippet)
        insert_before_marker(PAINTINGS_FILE, "paintings", snippet)
        changed = True
        published_url = "https://xinjuju.github.io/paintings.html"

    if "photo" in labels:
        title = sections["标题"]
        image_url = extract_image_url(sections.get("图片", ""))
        description = sections["说明"]
        if not image_url:
            raise ValueError("未找到图片地址。请把本地图片直接拖进“图片”一栏后再提交。")
        snippet = render_photo_card(title, image_url, description)
        remove_placeholder(INDEX_FILE, photo_placeholder)
        remove_placeholder(PHOTOS_FILE, photo_placeholder)
        insert_before_marker(INDEX_FILE, "photos", snippet)
        insert_before_marker(PHOTOS_FILE, "photos", snippet)
        changed = True
        published_url = "https://xinjuju.github.io/photos.html"

    if "note" in labels:
        title = sections["标题"]
        date = sections["日期"]
        body = sections["正文"]
        slug = slugify(title)
        filename = f"{slug}-{issue['number']}.html"
        post_path = POSTS_DIR / filename
        post_path.write_text(render_note_page(title, date, body), encoding="utf-8")
        href = f"posts/{filename}"
        snippet = render_note_card(title, href)
        insert_before_marker(INDEX_FILE, "notes", snippet)
        insert_before_marker(NOTES_FILE, "notes", snippet)
        changed = True
        published_url = f"https://xinjuju.github.io/{href}"

    write_output("changed", "true" if changed else "false")
    write_output("commit_message", commit_message)
    write_output("published_url", published_url)


if __name__ == "__main__":
    main()
