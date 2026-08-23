#!/usr/bin/env bash

set -euo pipefail

: "${GITHUB_TOKEN:?GITHUB_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${PAGES_BASE_URL:?PAGES_BASE_URL is required}"

CLEANUP_ONLY="${CLEANUP_ONLY:-false}"
GITHUB_SHA="${GITHUB_SHA:-}"
REF_NAME="${REF_NAME:-}"
REF_TYPE="${REF_TYPE:-}"
RELEASE_TAG="${RELEASE_TAG:-$REF_NAME}"
WORKSPACE_DIR="$(pwd)"
PAGES_DIR=/tmp/decktation-gh-pages
ZIP_SOURCE="$WORKSPACE_DIR/build-output/decktation.zip"

if [ "$CLEANUP_ONLY" != "true" ] && [ ! -f "$ZIP_SOURCE" ]; then
  echo "Missing build artifact: $ZIP_SOURCE" >&2
  exit 1
fi

if [ "$CLEANUP_ONLY" != "true" ]; then
  : "${GITHUB_SHA:?GITHUB_SHA is required}"
  : "${REF_NAME:?REF_NAME is required}"
  : "${REF_TYPE:?REF_TYPE is required}"
fi

normalize_ref() {
  printf '%s' "$1" | python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read(), safe=""))'
}

escape_json() {
  printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

write_metadata() {
  local output_path="$1"
  local channel="$2"
  local ref_value="$3"
  local zip_url="$4"
  cat >"$output_path" <<EOF
{
  "plugin": "Decktation",
  "channel": $(escape_json "$channel"),
  "ref": $(escape_json "$ref_value"),
  "commit": $(escape_json "$GITHUB_SHA"),
  "zip_url": $(escape_json "$zip_url"),
  "generated_at": $(escape_json "$(date -u +%FT%TZ)")
}
EOF
}

write_download_page() {
  local output_path="$1"
  local title="$2"
  local zip_url="$3"
  local metadata_url="$4"
  cat >"$output_path" <<EOF
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${title}</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f1ea;
      --card: rgba(255, 252, 247, 0.92);
      --ink: #1f2933;
      --muted: #52606d;
      --accent: #b44f2a;
      --accent-dark: #7c3318;
      --border: rgba(31, 41, 51, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(180, 79, 42, 0.16), transparent 28%),
        linear-gradient(135deg, #efe7da 0%, #f8f6f2 46%, #ece3d5 100%);
      display: grid;
      place-items: center;
      padding: 24px;
    }
    main {
      width: min(760px, 100%);
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 32px;
      box-shadow: 0 24px 70px rgba(31, 41, 51, 0.12);
      backdrop-filter: blur(10px);
    }
    h1 {
      margin: 0 0 12px;
      font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
      font-size: clamp(2rem, 5vw, 3rem);
      line-height: 0.98;
    }
    p {
      margin: 0 0 16px;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.55;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 24px 0;
    }
    a.button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 48px;
      padding: 0 18px;
      border-radius: 999px;
      text-decoration: none;
      font-weight: 700;
      color: #fffaf2;
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%);
    }
    a.link {
      color: var(--accent-dark);
      text-decoration-thickness: 2px;
      text-underline-offset: 3px;
    }
    code {
      font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
      font-size: 0.92rem;
    }
  </style>
</head>
<body>
  <main>
    <h1>${title}</h1>
    <p>Decky Loader should use the direct ZIP URL below. This page is only a human-friendly landing page.</p>
    <div class="actions">
      <a class="button" href="${zip_url}">Download decktation.zip</a>
      <a class="button" href="${metadata_url}">View metadata</a>
    </div>
    <p><strong>Direct ZIP URL</strong><br><code>${zip_url}</code></p>
    <p><a class="link" href="${PAGES_BASE_URL}/">Back to all Decktation downloads</a></p>
  </main>
</body>
</html>
EOF
}

render_index_list() {
  local section_dir="$1"
  local section_title="$2"
  local base_url="$3"

  if [ ! -d "$section_dir" ]; then
    return
  fi

  printf '<section><h2>%s</h2><ul>\n' "$section_title"
  find "$section_dir" -name metadata.json -print | sort | while read -r metadata; do
    local rel
    rel="${metadata#$PAGES_DIR/}"
    local dir
    dir="$(dirname "$rel")"
    local name
    name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ref"])' "$metadata")"
    printf '  <li><a href="%s/%s/">%s</a> <span>%s</span></li>\n' \
      "$base_url" "$dir" "$name" "$dir"
  done
  printf '</ul></section>\n'
}

cleanup_deleted_branch_dirs() {
  local branches_dir="$PAGES_DIR/branches"
  local remote_heads
  local normalized_heads

  mkdir -p "$branches_dir"
  remote_heads="$(git -C "$PAGES_DIR" ls-remote --heads origin)"
  normalized_heads="$(
    printf '%s\n' "$remote_heads" | while read -r _ ref; do
      normalize_ref "${ref#refs/heads/}"
    done
  )"

  find "$branches_dir" -mindepth 1 -maxdepth 1 -type d | while read -r branch_dir; do
    local branch_key
    branch_key="$(basename "$branch_dir")"
    if ! printf '%s\n' "$normalized_heads" | grep -Fxq "$branch_key"; then
      rm -rf "$branch_dir"
    fi
  done
}

checkout_pages_branch() {
  git clone --depth 1 --branch gh-pages \
    "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" \
    "$PAGES_DIR" 2>/dev/null || {
    git clone --depth 1 \
      "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" \
      "$PAGES_DIR"
    cd "$PAGES_DIR"
    git checkout --orphan gh-pages
    git rm -rf . >/dev/null 2>&1 || true
    cd - >/dev/null
  }
}

render_pages_content() {
  if [ "$CLEANUP_ONLY" != "true" ]; then
    local branch_key
    branch_key="$(normalize_ref "$REF_NAME")"
    mkdir -p "$PAGES_DIR/branches/$branch_key"
    cp "$ZIP_SOURCE" "$PAGES_DIR/branches/$branch_key/decktation.zip"
    write_metadata \
      "$PAGES_DIR/branches/$branch_key/metadata.json" \
      "branch" \
      "$REF_NAME" \
      "$PAGES_BASE_URL/branches/$branch_key/decktation.zip"
    write_download_page \
      "$PAGES_DIR/branches/$branch_key/index.html" \
      "Decktation branch build: $REF_NAME" \
      "$PAGES_BASE_URL/branches/$branch_key/decktation.zip" \
      "$PAGES_BASE_URL/branches/$branch_key/metadata.json"
  fi

  cleanup_deleted_branch_dirs

  if [ "$CLEANUP_ONLY" != "true" ] && [ "$REF_TYPE" = "tag" ]; then
    mkdir -p "$PAGES_DIR/releases/$RELEASE_TAG" "$PAGES_DIR/releases/latest"
    cp "$ZIP_SOURCE" "$PAGES_DIR/releases/$RELEASE_TAG/decktation.zip"
    cp "$ZIP_SOURCE" "$PAGES_DIR/releases/latest/decktation.zip"
    # Short, stable install URL for Decky's "Install Plugin from URL" action.
    # Only release tags update it; branch builds must never replace the stable
    # artifact a user receives from this address.
    cp "$ZIP_SOURCE" "$PAGES_DIR/latest.zip"
    write_metadata \
      "$PAGES_DIR/releases/$RELEASE_TAG/metadata.json" \
      "release" \
      "$RELEASE_TAG" \
      "$PAGES_BASE_URL/releases/$RELEASE_TAG/decktation.zip"
    write_metadata \
      "$PAGES_DIR/releases/latest/metadata.json" \
      "release-latest" \
      "$RELEASE_TAG" \
      "$PAGES_BASE_URL/releases/latest/decktation.zip"
    write_download_page \
      "$PAGES_DIR/releases/$RELEASE_TAG/index.html" \
      "Decktation release build: $RELEASE_TAG" \
      "$PAGES_BASE_URL/releases/$RELEASE_TAG/decktation.zip" \
      "$PAGES_BASE_URL/releases/$RELEASE_TAG/metadata.json"
    write_download_page \
      "$PAGES_DIR/releases/latest/index.html" \
      "Decktation latest release" \
      "$PAGES_BASE_URL/releases/latest/decktation.zip" \
      "$PAGES_BASE_URL/releases/latest/metadata.json"
  fi

  cat >"$PAGES_DIR/index.html" <<EOF
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Decktation Downloads</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f1ea;
      --card: rgba(255, 252, 247, 0.92);
      --ink: #1f2933;
      --muted: #52606d;
      --accent: #b44f2a;
      --border: rgba(31, 41, 51, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(180, 79, 42, 0.16), transparent 32%),
        linear-gradient(150deg, #efe7da 0%, #f8f6f2 50%, #ece3d5 100%);
      padding: 32px 20px 48px;
    }
    main {
      width: min(920px, 100%);
      margin: 0 auto;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 32px;
      box-shadow: 0 24px 70px rgba(31, 41, 51, 0.12);
      backdrop-filter: blur(10px);
    }
    h1, h2 {
      font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
    }
    h1 {
      margin: 0 0 12px;
      font-size: clamp(2.2rem, 6vw, 4rem);
      line-height: 0.94;
    }
    h2 {
      margin: 28px 0 10px;
      font-size: 1.3rem;
    }
    p, li, code, span {
      color: var(--muted);
      line-height: 1.55;
    }
    .hero {
      display: grid;
      gap: 16px;
    }
    .panel {
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
      background: rgba(255, 255, 255, 0.5);
    }
    ul {
      margin: 0;
      padding-left: 20px;
    }
    li + li {
      margin-top: 8px;
    }
    a {
      color: var(--accent);
      text-decoration-thickness: 2px;
      text-underline-offset: 3px;
    }
    code {
      font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
      font-size: 0.92rem;
    }
  </style>
</head>
<body>
  <main>
    <div class="hero">
      <div>
        <h1>Decktation Downloads</h1>
        <p>Stable, direct ZIP URLs for Decky Loader installs. Use the ZIP URLs directly with Decky's <strong>Install Plugin from URL</strong> flow.</p>
      </div>
      <div class="panel">
        <p><strong>Short install URL</strong><br><code>${PAGES_BASE_URL}/latest.zip</code></p>
        <p><strong>Latest release ZIP</strong><br><code>${PAGES_BASE_URL}/releases/latest/decktation.zip</code></p>
        <p><strong>Branch ZIP pattern</strong><br><code>${PAGES_BASE_URL}/branches/&lt;url-encoded-branch-name&gt;/decktation.zip</code></p>
      </div>
    </div>
    $(render_index_list "$PAGES_DIR/releases" "Releases" "$PAGES_BASE_URL")
    $(render_index_list "$PAGES_DIR/branches" "Branches" "$PAGES_BASE_URL")
  </main>
</body>
</html>
EOF

  touch "$PAGES_DIR/.nojekyll"
}

publish_pages() {
  cd "$PAGES_DIR"
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

  if git status --short | grep -q .; then
    git add .
    git commit -m "Publish downloads for $REF_TYPE $REF_NAME"
    git push origin gh-pages
  else
    echo "No gh-pages changes to publish."
  fi
}

for attempt in 1 2 3; do
  # Never remove the directory that is the shell's current working directory.
  # A failed push retries from a fresh checkout of the updated gh-pages head.
  cd /
  rm -rf "$PAGES_DIR"
  checkout_pages_branch
  render_pages_content
  if publish_pages; then
    exit 0
  fi
  if [ "$attempt" -lt 3 ]; then
    echo "Retrying gh-pages publish after concurrent update..."
    sleep 5
  fi
done

echo "Failed to publish gh-pages after 3 attempts." >&2
exit 1
