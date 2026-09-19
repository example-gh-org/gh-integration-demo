#!/usr/bin/env bash
# Convert every markdown file under the knowledge base (any depth) to a
# standalone HTML page, mirroring the folder layout, and generate an index
# page that links to each of them.
#
# Usage: scripts/build-site.sh <source-dir> <output-dir>
set -euo pipefail

SRC="${1:-knowledge-base}"
OUT="${2:-_site}"

rm -rf "$OUT"
mkdir -p "$OUT"
cp scripts/style.css "$OUT/style.css"

html_escape() {
  sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' <<<"$1"
}

links=""
count=0
while IFS= read -r -d '' md; do
  rel="${md#"$SRC"/}"
  rel="${rel%.md}"
  out="$OUT/$rel.html"
  mkdir -p "$(dirname "$out")"

  # First H1 becomes the page title; fall back to the file name.
  title="$(grep -m1 '^# ' "$md" | sed 's/^# //' || true)"
  title="${title:-$(basename "$rel")}"

  # Nested pages need a relative path back up to the shared stylesheet.
  css="style.css"
  dir="$(dirname "$rel")"
  if [[ "$dir" != "." ]]; then
    depth="$(tr -cd '/' <<<"$dir/" | wc -c | tr -d ' ')"
    css="$(printf '../%.0s' $(seq 1 "$depth"))style.css"
  fi

  pandoc "$md" \
    --from gfm \
    --to html5 \
    --standalone \
    --metadata title="$title" \
    --css "$css" \
    --output "$out"

  href="$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$rel.html")"
  folder=""
  if [[ "$dir" != "." ]]; then
    folder=" <small>$(html_escape "$dir")</small>"
  fi
  links+="<li><a href=\"$href\">$(html_escape "$title")</a>$folder</li>"
  count=$((count + 1))
done < <(find "$SRC" -name '*.md' -print0 | sort -z)

if [[ "$count" -eq 0 ]]; then
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

echo "Built $count pages into $OUT/"
