#!/usr/bin/env python3
"""Build the knowledge-base website.

Every markdown file under the source folder becomes one HTML page, mirroring
the folder layout. Pages share a sidebar that lists the whole knowledge base
grouped by folder, a breadcrumb trail, an on-page table of contents, and
previous/next links. The index page presents each section as a card.

Only the standard library and the pandoc binary are needed.

Usage: scripts/build_site.py <source-dir> <output-dir>
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

SITE_TITLE = "Travel Knowledge Base"
SITE_TAGLINE = "Field notes for Tokyo, Kyoto and beyond, published straight from the Edra knowledge base."
REPO_URL = "https://github.com/example-gh-org/gh-integration-demo"
WORDS_PER_MINUTE = 200
# Section names that read better than a title-cased folder name.
SECTION_NAMES = {"day-trips": "Day trips", "sim-seed": "Simulation seed"}
ROOT_SECTION = "Start here"
# Sections listed in this order first; any others follow alphabetically.
SECTION_ORDER = ["tokyo", "kyoto"]


@dataclass
class Article:
    source: Path
    rel: str  # path without extension, e.g. "tokyo/food/ramen"
    title: str
    body_html: str
    headings: list[tuple[str, str]]  # (id, text) of every h2
    words: int
    updated: str | None
    section: str  # first folder, or "" for root articles
    subsection: str  # second folder, or ""

    @property
    def href(self) -> str:
        return urllib.parse.quote(f"{self.rel}.html")

    @property
    def depth(self) -> int:
        return self.rel.count("/")

    @property
    def root(self) -> str:
        return "../" * self.depth

    @property
    def minutes(self) -> int:
        return max(1, round(self.words / WORDS_PER_MINUTE))


def section_name(folder: str) -> str:
    if folder in SECTION_NAMES:
        return SECTION_NAMES[folder]
    return folder.replace("-", " ").replace("_", " ").capitalize()


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def run_pandoc(markdown: str) -> str:
    completed = subprocess.run(
        ["pandoc", "--from", "gfm", "--to", "html5", "--wrap=none"],
        input=markdown,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def git_updated(path: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


_H2 = re.compile(r'<h2 id="([^"]+)">(.*?)</h2>', re.DOTALL)
_TAG = re.compile(r"<[^>]+>")


def load_article(source: Path, src_root: Path) -> Article:
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = None
    for index, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            del lines[index]
            break
    rel = source.relative_to(src_root).with_suffix("").as_posix()
    if title is None:
        title = Path(rel).name.replace("-", " ").capitalize()
    markdown = "\n".join(lines).strip() + "\n"
    body_html = run_pandoc(markdown)
    headings = [
        (anchor, _TAG.sub("", label)) for anchor, label in _H2.findall(body_html)
    ]
    parts = rel.split("/")
    return Article(
        source=source,
        rel=rel,
        title=title,
        body_html=body_html,
        headings=headings,
        words=len(_TAG.sub(" ", body_html).split()),
        updated=git_updated(source),
        section=parts[0] if len(parts) > 1 else "",
        subsection=parts[1] if len(parts) > 2 else "",
    )


@dataclass
class Section:
    key: str
    name: str
    articles: list[Article] = field(default_factory=list)

    def grouped(self) -> list[tuple[str, list[Article]]]:
        groups: dict[str, list[Article]] = {}
        for article in self.articles:
            groups.setdefault(article.subsection, []).append(article)
        # Ungrouped articles first, then subsections alphabetically.
        return sorted(groups.items(), key=lambda item: (item[0] != "", item[0]))


def build_sections(articles: list[Article]) -> list[Section]:
    sections: dict[str, Section] = {}
    for article in articles:
        key = article.section
        if key not in sections:
            sections[key] = Section(key=key, name=section_name(key) if key else ROOT_SECTION)
        sections[key].articles.append(article)
    def rank(section: Section) -> tuple[int, int, str]:
        if not section.key:
            return (0, 0, "")
        if section.key in SECTION_ORDER:
            return (1, SECTION_ORDER.index(section.key), "")
        return (2, 0, section.key)

    return sorted(sections.values(), key=rank)


def ordered(sections: list[Section]) -> list[Article]:
    result: list[Article] = []
    for section in sections:
        for _, group in section.grouped():
            result.extend(group)
    return result


# ----------------------------------------------------------------- rendering


def render_nav(sections: list[Section], current: Article | None, root: str) -> str:
    parts = ['<nav class="sidebar-nav" aria-label="Knowledge base">']
    for section in sections:
        is_open = current is not None and current.section == section.key
        parts.append(f'<details class="nav-section"{" open" if is_open or not section.key else ""}>')
        parts.append(f"<summary>{esc(section.name)}<span class=\"count\">{len(section.articles)}</span></summary>")
        for subsection, group in section.grouped():
            if subsection:
                parts.append(f'<p class="nav-group">{esc(section_name(subsection))}</p>')
            parts.append("<ul>")
            for article in group:
                active = ' aria-current="page"' if article is current else ""
                parts.append(f'<li><a href="{root}{article.href}"{active}>{esc(article.title)}</a></li>')
            parts.append("</ul>")
        parts.append("</details>")
    parts.append("</nav>")
    return "\n".join(parts)


def render_breadcrumbs(article: Article) -> str:
    crumbs = [f'<a href="{article.root}index.html">Home</a>']
    if article.section:
        crumbs.append(f'<a href="{article.root}index.html#{esc(article.section)}">{esc(section_name(article.section))}</a>')
    if article.subsection:
        crumbs.append(f"<span>{esc(section_name(article.subsection))}</span>")
    return '<nav class="breadcrumbs" aria-label="Breadcrumb">' + ' <span class="sep">/</span> '.join(crumbs) + "</nav>"


def render_toc(article: Article) -> str:
    if len(article.headings) < 2:
        return ""
    items = "".join(f'<li><a href="#{esc(anchor)}">{esc(text)}</a></li>' for anchor, text in article.headings)
    return f'<aside class="toc" aria-label="On this page"><p class="toc-title">On this page</p><ul>{items}</ul></aside>'


def render_pager(prev: Article | None, nxt: Article | None, root: str) -> str:
    left = (
        f'<a class="pager-link prev" href="{root}{prev.href}"><span class="pager-label">Previous</span><span class="pager-title">{esc(prev.title)}</span></a>'
        if prev
        else "<span></span>"
    )
    right = (
        f'<a class="pager-link next" href="{root}{nxt.href}"><span class="pager-label">Next</span><span class="pager-title">{esc(nxt.title)}</span></a>'
        if nxt
        else "<span></span>"
    )
    return f'<nav class="pager" aria-label="Previous and next">{left}{right}</nav>'


FAVICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%E2%9B%A9%3C/text%3E%3C/svg%3E"


def render_shell(*, title: str, description: str, root: str, nav: str, main: str, aside: str = "", body_class: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="theme-color" content="#b23a2e">
<link rel="icon" href="{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap">
<link rel="stylesheet" href="{root}style.css">
</head>
<body class="{body_class}">
<a class="skip" href="#content">Skip to content</a>
<header class="topbar">
  <button class="menu-toggle" type="button" aria-controls="sidebar" aria-expanded="false">
    <span class="menu-icon" aria-hidden="true"></span> Menu
  </button>
  <a class="brand" href="{root}index.html"><span class="brand-mark" aria-hidden="true">⛩</span> {esc(SITE_TITLE)}</a>
  <a class="topbar-link" href="{REPO_URL}" rel="noopener">GitHub</a>
</header>
<div class="layout">
  <div class="sidebar" id="sidebar">
    {nav}
  </div>
  <main class="content" id="content">
    {main}
  </main>
  {aside}
</div>
<footer class="site-footer">
  <p>Published from the Edra knowledge base by GitHub Actions. Content changes are made on the platform and mirrored here automatically.</p>
</footer>
<script>
(function () {{
  var toggle = document.querySelector('.menu-toggle');
  var body = document.body;
  toggle.addEventListener('click', function () {{
    var open = body.classList.toggle('nav-open');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }});
  var current = document.querySelector('.sidebar [aria-current="page"]');
  if (current) current.scrollIntoView({{ block: 'center' }});
}})();
</script>
</body>
</html>
"""


def render_article_page(article: Article, sections: list[Section], prev: Article | None, nxt: Article | None) -> str:
    meta_bits = []
    if article.updated:
        meta_bits.append(f"Updated {esc(article.updated)}")
    meta_bits.append(f"{article.minutes} min read")
    meta = " · ".join(meta_bits)
    source_url = f"{REPO_URL}/blob/main/{urllib.parse.quote(article.source.as_posix())}"
    main = f"""{render_breadcrumbs(article)}
    <article class="article">
      <header class="article-header">
        <h1>{esc(article.title)}</h1>
        <p class="article-meta">{meta} · <a href="{source_url}" rel="noopener">Source</a></p>
      </header>
      <div class="prose">
{article.body_html}
      </div>
    </article>
    {render_pager(prev, nxt, article.root)}"""
    description = _TAG.sub(" ", article.body_html).split()
    return render_shell(
        title=f"{article.title} · {SITE_TITLE}",
        description=" ".join(description[:30]),
        root=article.root,
        nav=render_nav(sections, article, article.root),
        main=main,
        aside=render_toc(article),
        body_class="page-article",
    )


def render_index(sections: list[Section], total: int) -> str:
    cards = []
    for section in sections:
        groups = []
        for subsection, group in section.grouped():
            heading = f'<h3>{esc(section_name(subsection))}</h3>' if subsection else ""
            links = "".join(f'<li><a href="{article.href}">{esc(article.title)}</a></li>' for article in group)
            groups.append(f"{heading}<ul>{links}</ul>")
        cards.append(
            f'<section class="card" id="{esc(section.key or "start")}">'
            f'<header class="card-header"><h2>{esc(section.name)}</h2><span class="count">{len(section.articles)} article{"s" if len(section.articles) != 1 else ""}</span></header>'
            f'{"".join(groups)}</section>'
        )
    main = f"""<section class="hero">
      <p class="eyebrow">Knowledge base</p>
      <h1>{esc(SITE_TITLE)}</h1>
      <p class="lede">{esc(SITE_TAGLINE)}</p>
      <p class="hero-meta">{total} articles across {len([s for s in sections if s.key])} sections</p>
    </section>
    <div class="cards">
      {"".join(cards)}
    </div>"""
    return render_shell(
        title=SITE_TITLE,
        description=SITE_TAGLINE,
        root="",
        nav=render_nav(sections, None, ""),
        main=main,
        body_class="page-index",
    )


# ---------------------------------------------------------------------- main


def main(argv: list[str]) -> int:
    src_root = Path(argv[1] if len(argv) > 1 else "knowledge-base")
    out_root = Path(argv[2] if len(argv) > 2 else "_site")
    if shutil.which("pandoc") is None:
        print("pandoc is required but not on PATH", file=sys.stderr)
        return 1

    sources = sorted(src_root.rglob("*.md"))
    if not sources:
        print(f"No markdown files found in {src_root}", file=sys.stderr)
        return 1

    articles = [load_article(source, src_root) for source in sources]
    sections = build_sections(articles)
    sequence = ordered(sections)

    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)
    shutil.copy(Path(__file__).with_name("style.css"), out_root / "style.css")
    (out_root / ".nojekyll").touch()

    for position, article in enumerate(sequence):
        prev = sequence[position - 1] if position > 0 else None
        nxt = sequence[position + 1] if position + 1 < len(sequence) else None
        target = out_root / f"{article.rel}.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_article_page(article, sections, prev, nxt), encoding="utf-8")

    (out_root / "index.html").write_text(render_index(sections, len(articles)), encoding="utf-8")
    print(f"Built {len(articles)} pages into {out_root}/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
