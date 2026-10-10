import type { APIRoute } from 'astro';
import { locales } from '../i18n';
export const GET: APIRoute = ({ site }) => new Response(
  '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
  locales.map(lang => `<url><loc>${new URL(lang === 'en' ? '/' : `/${lang}/`, site)}</loc></url>`).join('') + '</urlset>',
  { headers: { 'Content-Type': 'application/xml' } },
);
