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
PR_NUMBER="${PR_NUMBER:-}"
PR_RUN_ID="${PR_RUN_ID:-}"
PR_RUN_ATTEMPT="${PR_RUN_ATTEMPT:-}"
PR_HEAD_REPO="${PR_HEAD_REPO:-}"
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
  if [ "$REF_TYPE" = "pull_request" ]; then
    [[ "$PR_NUMBER" =~ ^[1-9][0-9]*$ && "$PR_RUN_ID" =~ ^[1-9][0-9]*$ && "$PR_RUN_ATTEMPT" =~ ^[1-9][0-9]*$ ]] || exit 1
    [ -n "$PR_HEAD_REPO" ] || exit 1
  fi
fi

normalize_ref() {
  python3 "$WORKSPACE_DIR/scripts/branch-slug.py" "$1"
}

encode_url_path() {
  python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe="/"))' "$1"
}

escape_json() {
  printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

escape_html() {
  python3 -c 'import html,sys; print(html.escape(sys.argv[1], quote=True))' "$1"
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
  title="$(escape_html "$title")"
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
      <a class="button" href="${zip_url}">Download Decktation.zip</a>
      <a class="button" href="${metadata_url}">View metadata</a>
    </div>
    <p><strong>Direct ZIP URL</strong><br><code>${zip_url}</code></p>
    <p><a class="link" href="${PAGES_BASE_URL}/downloads/">Back to all Decktation downloads</a></p>
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
    name="$(escape_html "$name")"
    local url_dir
    url_dir="$(encode_url_path "$dir")"
    printf '  <li><a href="%s/%s/">%s</a> <span>%s</span></li>\n' \
      "$base_url" "$url_dir" "$name" "$(escape_html "$dir")"
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

refresh_branch_pages() {
  local branches_dir="$PAGES_DIR/branches"
  [ -d "$branches_dir" ] || return 0

  find "$branches_dir" -mindepth 2 -maxdepth 2 -type f -name metadata.json -print | while read -r metadata; do
    local relative_dir
    relative_dir="$(dirname "${metadata#"$PAGES_DIR"/}")"
    local url_dir
    url_dir="$(encode_url_path "$relative_dir")"
    # Also repair existing branch downloads when publishing another branch.
    local download_dir
    download_dir="$(dirname "$metadata")"
    if [ -f "$download_dir/decktation.zip" ]; then
      cp "$download_dir/decktation.zip" "$download_dir/Decktation.zip"
    fi
    local zip_url="$PAGES_BASE_URL/$url_dir/Decktation.zip"
    local metadata_url="$PAGES_BASE_URL/$url_dir/metadata.json"
    local branch_name
    branch_name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ref"])' "$metadata")"

    python3 - "$metadata" "$zip_url" <<'PY'
import json
import sys
from pathlib import Path

metadata_path = Path(sys.argv[1])
data = json.loads(metadata_path.read_text())
data["zip_url"] = sys.argv[2]
metadata_path.write_text(json.dumps(data, indent=2) + "\n")
PY

    write_download_page \
      "$(dirname "$metadata")/index.html" \
      "Decktation branch build: $branch_name" \
      "$zip_url" \
      "$metadata_url"
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

migrate_branch_dirs() {
  python3 - "$PAGES_DIR/branches" "$WORKSPACE_DIR/scripts/branch-slug.py" <<'PY_MIGRATE'
import importlib.util, json, sys
from pathlib import Path
root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("branch_slug", sys.argv[2])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
planned = {}
for metadata in sorted(root.glob("*/metadata.json")):
    ref = json.loads(metadata.read_text())["ref"]
    slug = module.branch_slug(ref)
    if slug in planned and planned[slug][1] != ref:
        raise SystemExit(f"Branch URL collision: {ref} and {planned[slug][1]}")
    planned[slug] = (metadata.parent, ref)
for slug, (source, ref) in planned.items():
    target = root / slug
    if source != target:
        if target.exists():
            raise SystemExit(f"Migration target already exists: {target}")
        source.rename(target)
PY_MIGRATE
}

assert_branch_target_available() {
  local branch_key="$1"
  local metadata="$PAGES_DIR/branches/$branch_key/metadata.json"
  if [ ! -f "$metadata" ]; then
    return
  fi
  local existing_ref
  existing_ref="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ref"])' "$metadata")"
  if [ "$existing_ref" != "$REF_NAME" ]; then
    echo "Branch URL collision: $REF_NAME and $existing_ref both use $branch_key" >&2
    exit 1
  fi
}

assert_release_is_not_older() {
  local latest="$PAGES_DIR/releases/latest/metadata.json"
  [ "$REF_TYPE" = "tag" ] && [ -f "$latest" ] || return 0
  python3 - "$RELEASE_TAG" "$GITHUB_SHA" "$latest" "$WORKSPACE_DIR/scripts/generate-store-catalog.py" <<'PY_RELEASE_ORDER'
import importlib.util
import json
import sys

new_tag, new_sha, metadata, catalog_script = sys.argv[1:]
spec = importlib.util.spec_from_file_location('store_catalog', catalog_script)
store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store)
old = json.load(open(metadata, encoding='utf-8'))
old_tag = old['ref']
if not new_tag.startswith('v') or not old_tag.startswith('v'):
    raise SystemExit('Refusing invalid release tag')
new_version, old_version = new_tag[1:], old_tag[1:]
if (store.compare_versions({'name': new_version}, {'name': old_version}) < 0 or
        (new_tag == old_tag and old.get('commit') != new_sha)):
    raise SystemExit('Refusing older release or rewritten tag to protect latest download')
PY_RELEASE_ORDER
}

render_pr_content() {
  local dir="$PAGES_DIR/pulls/$PR_NUMBER/$PR_RUN_ID/$PR_RUN_ATTEMPT"
  local url="$PAGES_BASE_URL/pulls/$PR_NUMBER/$PR_RUN_ID/$PR_RUN_ATTEMPT/Decktation.zip"
  if [ -e "$dir/Decktation.zip" ] && ! cmp -s "$ZIP_SOURCE" "$dir/Decktation.zip"; then
    echo "Refusing to overwrite immutable PR ZIP" >&2
    return 1
  fi
  mkdir -p "$dir"
  cp "$ZIP_SOURCE" "$dir/Decktation.zip"
  local digest
  digest="$(sha256sum "$dir/Decktation.zip")"
  digest="${digest%% *}"
  PR_ZIP_URL="$url" PR_ZIP_SHA256="$digest" python3 - "$dir/metadata.json" <<'PY_PR_METADATA'
import json, os, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({
    'channel': 'pull_request', 'number': int(os.environ['PR_NUMBER']),
    'run_id': int(os.environ['PR_RUN_ID']), 'run_attempt': int(os.environ['PR_RUN_ATTEMPT']),
    'commit': os.environ['GITHUB_SHA'],
    'head_repository': os.environ['PR_HEAD_REPO'],
    'zip_url': os.environ['PR_ZIP_URL'], 'sha256': os.environ['PR_ZIP_SHA256'],
}, indent=2) + '\n')
PY_PR_METADATA
}

render_pages_content() {
  if [ "$CLEANUP_ONLY" != "true" ] && [ "$REF_TYPE" = "pull_request" ]; then
    render_pr_content
  fi
  assert_release_is_not_older
  migrate_branch_dirs
  if [ "$CLEANUP_ONLY" != "true" ] && [ "$REF_TYPE" != "pull_request" ]; then
    local branch_key
    branch_key="$(normalize_ref "$REF_NAME")"
    assert_branch_target_available "$branch_key"
    local branch_url_path
    branch_url_path="$(encode_url_path "branches/$branch_key")"
    local zip_url="$PAGES_BASE_URL/$branch_url_path/Decktation.zip"
    local metadata_url="$PAGES_BASE_URL/$branch_url_path/metadata.json"
    mkdir -p "$PAGES_DIR/branches/$branch_key"
    cp "$ZIP_SOURCE" "$PAGES_DIR/branches/$branch_key/decktation.zip"
    cp "$ZIP_SOURCE" "$PAGES_DIR/branches/$branch_key/Decktation.zip"
    write_metadata \
      "$PAGES_DIR/branches/$branch_key/metadata.json" \
      "branch" \
      "$REF_NAME" \
      "$zip_url"
    write_download_page \
      "$PAGES_DIR/branches/$branch_key/index.html" \
      "Decktation branch build: $REF_NAME" \
      "$zip_url" \
      "$metadata_url"
  fi

  cleanup_deleted_branch_dirs
  refresh_branch_pages

  if [ "$CLEANUP_ONLY" != "true" ] && [ "$REF_TYPE" = "tag" ]; then
    mkdir -p "$PAGES_DIR/releases/$RELEASE_TAG" "$PAGES_DIR/releases/latest" \
      "$PAGES_DIR/store"
    cp "$ZIP_SOURCE" "$PAGES_DIR/releases/$RELEASE_TAG/decktation.zip"
    cp "$ZIP_SOURCE" "$PAGES_DIR/releases/$RELEASE_TAG/Decktation.zip"
    cp "$ZIP_SOURCE" "$PAGES_DIR/releases/latest/decktation.zip"
    cp "$ZIP_SOURCE" "$PAGES_DIR/releases/latest/Decktation.zip"
    # Short, stable install URL for Decky's "Install Plugin from URL" action.
    # Only release tags update it; branch builds must never replace the stable
    # artifact a user receives from this address.
    cp "$ZIP_SOURCE" "$PAGES_DIR/latest.zip"
    write_metadata \
      "$PAGES_DIR/releases/$RELEASE_TAG/metadata.json" \
      "release" \
      "$RELEASE_TAG" \
      "$PAGES_BASE_URL/releases/$RELEASE_TAG/Decktation.zip"
    write_metadata \
      "$PAGES_DIR/releases/latest/metadata.json" \
      "release-latest" \
      "$RELEASE_TAG" \
      "$PAGES_BASE_URL/releases/latest/Decktation.zip"
    write_download_page \
      "$PAGES_DIR/releases/$RELEASE_TAG/index.html" \
      "Decktation release build: $RELEASE_TAG" \
      "$PAGES_BASE_URL/releases/$RELEASE_TAG/Decktation.zip" \
      "$PAGES_BASE_URL/releases/$RELEASE_TAG/metadata.json"
    write_download_page \
      "$PAGES_DIR/releases/latest/index.html" \
      "Decktation latest release" \
      "$PAGES_BASE_URL/releases/latest/Decktation.zip" \
      "$PAGES_BASE_URL/releases/latest/metadata.json"
  fi

  if [ "$CLEANUP_ONLY" != "true" ] && { [ "$REF_TYPE" = "tag" ] || [ "$REF_NAME" = "master" ]; }; then
    local catalog_artifact_url
    if [ "$REF_TYPE" = "tag" ]; then
      catalog_artifact_url="$PAGES_BASE_URL/releases/$RELEASE_TAG/Decktation.zip"
    else
      catalog_artifact_url="$PAGES_BASE_URL/branches/master/Decktation.zip"
    fi
    mkdir -p "$PAGES_DIR/store"
    local catalog_plugin_manifest="$WORKSPACE_DIR/plugin.json"
    local catalog_package_manifest="$WORKSPACE_DIR/package.json"
    if [ "$REF_TYPE" = "tag" ]; then
      # Trusted publisher code is checked out from master; release manifests
      # must still reflect the built tag rather than today's master version.
      git -C "$WORKSPACE_DIR" fetch origin "refs/tags/$RELEASE_TAG"
      local tag_manifests
      tag_manifests="$(mktemp -d)"
      git -C "$WORKSPACE_DIR" show "$GITHUB_SHA:plugin.json" >"$tag_manifests/plugin.json"
      git -C "$WORKSPACE_DIR" show "$GITHUB_SHA:package.json" >"$tag_manifests/package.json"
      catalog_plugin_manifest="$tag_manifests/plugin.json"
      catalog_package_manifest="$tag_manifests/package.json"
    fi
    python3 "$WORKSPACE_DIR/scripts/generate-store-catalog.py" \
      --plugin-manifest "$catalog_plugin_manifest" \
      --package-manifest "$catalog_package_manifest" \
      --artifact "$ZIP_SOURCE" \
      --artifact-url "$catalog_artifact_url" \
      --github-repository "$GITHUB_REPOSITORY" \
      --output "$PAGES_DIR/store/plugins.json"
    if [ "$REF_TYPE" = "tag" ]; then rm -rf "$tag_manifests"; fi
  fi

  # Keep the stable short URL's filename equal to plugin.json's name.
  # Migrate existing releases too, without changing which release is latest.
  if [ -f "$PAGES_DIR/latest.zip" ]; then
    cp "$PAGES_DIR/latest.zip" "$PAGES_DIR/Decktation.zip"
  fi
  if [ -d "$PAGES_DIR/releases" ]; then
    find "$PAGES_DIR/releases" -type f -name decktation.zip -print | while read -r artifact; do
      cp "$artifact" "$(dirname "$artifact")/Decktation.zip"
    done
  fi

  mkdir -p "$PAGES_DIR/downloads"
  cat >"$PAGES_DIR/downloads/index.html" <<EOF
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
        <p><strong>Short install URL</strong><br><a href="${PAGES_BASE_URL}/Decktation.zip">${PAGES_BASE_URL}/Decktation.zip</a></p>
        <p><strong>Latest release ZIP</strong><br><code>${PAGES_BASE_URL}/releases/latest/Decktation.zip</code></p>
        <p><strong>Decky Custom Store URL</strong><br><a href="https://decktation.com/plugins.json">https://decktation.com/plugins.json</a></p>
        <p><strong>Branch ZIP pattern</strong><br><code>${PAGES_BASE_URL}/branches/&lt;branch-slug&gt;/Decktation.zip</code></p>
      </div>
    </div>
    $(render_index_list "$PAGES_DIR/releases" "Releases" "$PAGES_BASE_URL")
    $(render_index_list "$PAGES_DIR/branches" "Branches" "$PAGES_BASE_URL")
  </main>
</body>
</html>
EOF

  # Landing owns the root; plugin builds only update the download catalog.
  if [ ! -f "$PAGES_DIR/index.html" ]; then
    cp "$PAGES_DIR/downloads/index.html" "$PAGES_DIR/index.html"
  fi

  touch "$PAGES_DIR/.nojekyll"
}

refresh_testing_catalog() {
  # Trusted publisher code queries live open PRs; no manual approval file.
  git -C "$WORKSPACE_DIR" fetch origin master
  local manifest heads
  manifest="$(mktemp)"
  heads="$(mktemp)"
  git -C "$WORKSPACE_DIR" show FETCH_HEAD:plugin.json >"$manifest"
  git -C "$WORKSPACE_DIR" ls-remote --heads origin >"$heads"
  python3 "$WORKSPACE_DIR/scripts/generate-pr-catalog.py" \
    --pages-root "$PAGES_DIR" \
    --current-refs "$heads" \
    --plugin-manifest "$manifest" \
    --repository "$GITHUB_REPOSITORY" \
    --base-url "$PAGES_BASE_URL" \
    --output "$PAGES_DIR/store/testing/plugins.json"
  rm -f "$manifest" "$heads"
}

publish_pages() (
  cd "$PAGES_DIR"
  # A newer push or deletion may happen while rendering this checkout.
  if [ "$CLEANUP_ONLY" != "true" ]; then
    if [ "$REF_TYPE" = "pull_request" ]; then
      python3 "$WORKSPACE_DIR/scripts/verify-current-pr.py" \
        --repository "$GITHUB_REPOSITORY" --number "$PR_NUMBER" \
        --sha "$GITHUB_SHA" --head-repository "$PR_HEAD_REPO" || {
          echo "PR closed or changed before publication" >&2
          return 1
        }
    else
      bash "$WORKSPACE_DIR/scripts/verify-current-ref.sh" \
        "https://github.com/${GITHUB_REPOSITORY}.git" "$REF_TYPE" "$REF_NAME" "$GITHUB_SHA" || {
          echo "Ref moved or was deleted before publication; refusing stale ZIP" >&2
          return 1
        }
    fi
  fi
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

  if git status --short | grep -q .; then
    git add .
    git commit -m "Publish downloads for $REF_TYPE $REF_NAME"
    git push origin gh-pages
  else
    echo "No gh-pages changes to publish."
  fi
  if [ "$CLEANUP_ONLY" != "true" ] && [ "$REF_TYPE" = "pull_request" ] && \
     ! python3 "$WORKSPACE_DIR/scripts/verify-current-pr.py" \
       --repository "$GITHUB_REPOSITORY" --number "$PR_NUMBER" \
       --sha "$GITHUB_SHA" --head-repository "$PR_HEAD_REPO"; then
    echo "PR moved during publication; removing stale catalog entry" >&2
    refresh_testing_catalog
    git add store/testing/plugins.json
    if ! git diff --cached --quiet; then
      git commit -m "Reconcile test catalog after PR moved"
      git push origin gh-pages
    fi
  fi
  # A ref may move between the pre-push check and the gh-pages push. Remove
  # its catalog entry promptly; Decky also verifies the pinned ZIP hash.
  if [ "$CLEANUP_ONLY" != "true" ] && [ "$REF_TYPE" = "branch" ] && \
     ! bash "$WORKSPACE_DIR/scripts/verify-current-ref.sh" \
       "https://github.com/${GITHUB_REPOSITORY}.git" "$REF_TYPE" "$REF_NAME" "$GITHUB_SHA"; then
    echo "Ref moved during publication; reconciling test catalog" >&2
    refresh_testing_catalog
    git add store/testing/plugins.json
    if ! git diff --cached --quiet; then
      git commit -m "Reconcile test catalog after branch moved"
      git push origin gh-pages
    fi
  fi
)

for attempt in 1 2 3; do
  # Never remove the directory that is the shell's current working directory.
  # A failed push retries from a fresh checkout of the updated gh-pages head.
  cd /
  rm -rf "$PAGES_DIR"
  checkout_pages_branch
  render_pages_content
  refresh_testing_catalog
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
