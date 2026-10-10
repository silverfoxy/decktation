import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import test from 'node:test';

const dist = new URL('../dist/', import.meta.url);
const source = new URL('../src/', import.meta.url);

test('localized pages contain working install, store, downloads, and asset links', () => {
  for (const [locale, route] of [['en', 'index.html'], ['es', 'es/index.html']]) {
    const page = readFileSync(new URL(route, dist), 'utf8');
    assert.match(page, new RegExp(`<html lang="${locale}"`));
    assert.ok(page.includes('https://decktation.com/Decktation.zip'));
    assert.ok(page.includes('https://decktation.com/plugins.json'));
    assert.ok(page.includes('href="/downloads/"'));
    assert.ok(!page.includes('{{'));
    assert.ok(!page.includes('&lt;br&gt;'));
    for (const [, path] of page.matchAll(/(?:src|href)="(\/(?:assets|vendor)\/[^"?#]+|\/(?:styles\.css|app\.js))[^" ]*"/g)) {
      assert.ok(existsSync(new URL(path.slice(1), dist)), `Missing asset ${path} in ${route}`);
    }
    const localeData = JSON.parse(readFileSync(new URL(`i18n/${locale}.json`, source), 'utf8'));
    assert.ok(page.includes(localeData['seo.title']));
    assert.ok(page.includes(localeData['install.storeTitle']));
  }
});

test('all translations have matching keys and the rendered page uses each content key', () => {
  const en = JSON.parse(readFileSync(new URL('i18n/en.json', source), 'utf8'));
  const es = JSON.parse(readFileSync(new URL('i18n/es.json', source), 'utf8'));
  assert.deepEqual(Object.keys(en).sort(), Object.keys(es).sort());
  const page = readFileSync(new URL('index.html', dist), 'utf8');
  for (const key of Object.keys(en)) {
    if (!/^(seo|copy|a11y)\./.test(key)) assert.ok(page.includes(`data-i18n="${key}"`), `Unused translation: ${key}`);
  }
});

test('canonical URLs, sitemap, and robots use the deployed site origin', () => {
  const base = process.env.SITE_BASE_URL || 'https://decktation.com';
  for (const [route, suffix] of [['index.html', '/'], ['es/index.html', '/es/']]) {
    assert.ok(readFileSync(new URL(route, dist), 'utf8').includes(`rel="canonical" href="${new URL(suffix, base)}"`));
  }
  assert.ok(readFileSync(new URL('robots.txt', dist), 'utf8').includes(`${base}/sitemap.xml`));
  assert.ok(readFileSync(new URL('sitemap.xml', dist), 'utf8').includes(`${base}/es/`));
});
