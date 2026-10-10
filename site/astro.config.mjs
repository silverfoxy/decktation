import { defineConfig } from 'astro/config';

export default defineConfig({
  site: process.env.SITE_BASE_URL || 'https://decktation.com',
  output: 'static',
  trailingSlash: 'always',
});
