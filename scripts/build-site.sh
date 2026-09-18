#!/usr/bin/env bash
# Convert every markdown file in the knowledge base to a standalone HTML page
# and generate an index page that links to each of them.
#
# Usage: scripts/build-site.sh <source-dir> <output-dir>
set -euo pipefail

SRC="${1:-knowledge-base}"
OUT="${2:-_site}"

rm -rf "$OUT"
mkdir -p "$OUT"
cp scripts/style.css "$OUT/style.css"

links=""
shopt -s nullglob
for md in "$SRC"/*.md; do
  name="$(basename "${md%.md}")"
  # First H1 becomes the page title; fall back to the file name.
  title="$(grep -m1 '^# ' "$md" | sed 's/^# //' || true)"
  title="${title:-$name}"
  pandoc "$md" \
    --from gfm \
    --to html5 \
    --standalone \
    --metadata title="$title" \
    --css style.css \
    --output "$OUT/$name.html"
  links+="<li><a href=\"$name.html\">$title</a></li>"
done

if [[ -z "$links" ]]; then
  echo "No markdown files found in $SRC" >&2
  exit 1
fi

cat > "$OUT/index.html" <<HTML
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Knowledge Base</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header id="title-block-header"><h1 class="title">Knowledge Base</h1></header>
<ul>$links</ul>
<footer><small>Generated from <code>$SRC/</code> by GitHub Actions.</small></footer>
</body>
</html>
HTML

echo "Built $(ls "$OUT"/*.html | wc -l | tr -d ' ') pages into $OUT/"
