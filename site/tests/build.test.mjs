import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import test from 'node:test';

const dist = new URL('../dist/', import.meta.url);
const source = new URL('../src/', import.meta.url);
const locales = readdirSync(new URL('i18n/', source)).filter(name => name.endsWith('.json')).map(name => name.slice(0, -5));

test('localized pages contain working install, downloads, and asset links', () => {
  for (const locale of locales) {
    const route = locale === 'en' ? 'index.html' : `${locale}/index.html`;
    const page = readFileSync(new URL(route, dist), 'utf8');
    assert.match(page, new RegExp(`<html lang="${locale}"`));
    assert.ok(page.includes('https://decktation.com/Decktation.zip'));
    assert.ok(!page.includes('https://decktation.com/plugins.json'));
    assert.ok(!page.includes('custom-store'));
    assert.ok(page.includes('href="/downloads/"'));
    assert.ok(!page.includes('{{'));
    assert.ok(!page.includes('&lt;br&gt;'));
    for (const [, path] of page.matchAll(/(?:src|href)="(\/(?:assets|vendor)\/[^"?#]+|\/(?:styles\.css|app\.js))[^" ]*"/g)) {
      assert.ok(existsSync(new URL(path.slice(1), dist)), `Missing asset ${path} in ${route}`);
    }
    const localeData = JSON.parse(readFileSync(new URL(`i18n/${locale}.json`, source), 'utf8'));
    assert.ok(page.includes(localeData['seo.title']));
    for (const language of locales) assert.ok(page.includes(`hreflang="${language}"`));
  }
});

test('all translations have matching keys and the rendered page uses each content key', () => {
  const en = JSON.parse(readFileSync(new URL('i18n/en.json', source), 'utf8'));
  for (const locale of locales) {
    const translated = JSON.parse(readFileSync(new URL(`i18n/${locale}.json`, source), 'utf8'));
    assert.deepEqual(Object.keys(en).sort(), Object.keys(translated).sort(), locale);
  }
  const page = readFileSync(new URL('index.html', dist), 'utf8');
  for (const key of Object.keys(en)) {
    if (!/^(seo|copy|a11y)\./.test(key)) assert.ok(page.includes(`data-i18n="${key}"`), `Unused translation: ${key}`);
  }
});

test('canonical URLs, sitemap, and robots use the deployed site origin', () => {
  const base = process.env.SITE_BASE_URL || 'https://decktation.com';
  for (const locale of locales) {
    const route = locale === 'en' ? 'index.html' : `${locale}/index.html`;
    const suffix = locale === 'en' ? '/' : `/${locale}/`;
    assert.ok(readFileSync(new URL(route, dist), 'utf8').includes(`rel="canonical" href="${new URL(suffix, base)}"`));
  }
  assert.ok(readFileSync(new URL('robots.txt', dist), 'utf8').includes(`${base}/sitemap.xml`));
  const sitemap = readFileSync(new URL('sitemap.xml', dist), 'utf8');
  for (const locale of locales) assert.ok(sitemap.includes(`${base}${locale === 'en' ? '/' : `/${locale}/`}`));
});

test('walkthrough is discoverable and ships interactive, accessible examples', () => {
  const walkthrough = readFileSync(new URL('walkthrough/index.html', dist), 'utf8');
  for (const lesson of ['first-message', 'channel-prefixes', 'slash-commands', 'spoken-punctuation', 'review']) {
    assert.ok(walkthrough.includes(`id="lesson-${lesson}"`));
    assert.ok(walkthrough.includes(`aria-controls="lesson-${lesson}"`));
  }
  assert.ok(walkthrough.includes('/p ready when you are'));
  assert.ok(walkthrough.includes('Send transcript'));
  assert.ok(walkthrough.includes('Cancel transcript'));
  assert.ok(walkthrough.includes('aria-live="polite"'));
  assert.ok(walkthrough.includes('Illustrative demos.'));
  const scripts = [...walkthrough.matchAll(/src="(\/_astro\/[^" ]+\.js)"/g)];
  assert.ok(scripts.length > 0 || (walkthrough.includes('<script type="module">') && walkthrough.includes('prefers-reduced-motion')), 'Tutorial must ship its playback controller');
  for (const [, path] of scripts) assert.ok(existsSync(new URL(path.slice(1), dist)));
  assert.ok(!walkthrough.includes('src="/app.js'), 'Landing-only scripts must not run on guide pages');
  for (const locale of locales) {
    const page = readFileSync(new URL(locale === 'en' ? 'index.html' : `${locale}/index.html`, dist), 'utf8');
    assert.ok(page.includes('href="/walkthrough/"'));
    assert.ok(page.includes('href="/changelog/"'));
  }
});

test('every documented release has complete notes, a canonical page, and sitemap entry', () => {
  const changelog = readFileSync(new URL('../../CHANGELOG.md', import.meta.url), 'utf8');
  const versions = [...changelog.matchAll(/^## \[([^\]]+)\]/gm)].map(match => match[1]);
  const index = readFileSync(new URL('changelog/index.html', dist), 'utf8');
  const sitemap = readFileSync(new URL('sitemap.xml', dist), 'utf8');
  const base = process.env.SITE_BASE_URL || 'https://decktation.com';
  for (const version of versions) {
    const path = `/changelog/${version.toLowerCase()}/`;
    const page = readFileSync(new URL(`${path.slice(1)}index.html`, dist), 'utf8');
    assert.ok(index.includes(`href="${path}"`));
    assert.ok(sitemap.includes(new URL(path, base).href));
    assert.ok(page.includes(`rel="canonical" href="${new URL(path, base)}"`));
    if (version === 'Unreleased') assert.ok(page.includes('Not released yet'));
    else assert.ok(page.includes(`https://github.com/silverfoxy/decktation/releases/tag/v${version}`));
  }
  assert.ok(index.includes('Initial packaged release'));
  assert.ok(index.includes('Legion Go S controller support'));
  assert.ok(!index.includes('[Unreleased]:'));
  assert.ok(sitemap.includes(new URL('/walkthrough/', base).href));
});

test('tutorial popup exports match the live renderer and include every native state', async () => {
  const { createHash } = await import('node:crypto');
  const manifest = JSON.parse(readFileSync(new URL('../public/assets/app-overlays/manifest.json', import.meta.url), 'utf8'));
  const hash = value => createHash('sha256').update(value).digest('hex');
  for (const [path, expected] of Object.entries(manifest.sources)) {
    assert.equal(hash(readFileSync(new URL(`../../${path}`, import.meta.url))), expected,
      `${path} changed: run /usr/bin/python3 scripts/export_website_overlays.py`);
  }
  const sprite = readFileSync(new URL('assets/app-overlays/sprite.svg', dist), 'utf8');
  assert.equal(hash(sprite), manifest.spriteSha256);
  for (let frame = 0; frame < manifest.frames; frame++) assert.ok(sprite.includes(`id="recording-${frame}"`));
  for (const state of ['transcribing', 'review', 'sent', 'cancelled', 'typed']) assert.ok(sprite.includes(`id="${state}"`));
  for (const dimensions of Object.values(manifest.dimensions)) {
    assert.deepEqual(dimensions.viewBox.split(' ').slice(0, 2), ['0', '0'], 'Browser viewport must not apply the native crop twice');
  }
  const ids = [...sprite.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length, 'Cairo glyph IDs must not collide between exported states');
  assert.ok(!sprite.includes('<script'));
  assert.ok(readFileSync(new URL('walkthrough/index.html', dist), 'utf8').includes('/assets/app-overlays/sprite.svg#recording-0'));
});
