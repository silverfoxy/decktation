import changelog from '../../../CHANGELOG.md?raw';
import { marked } from 'marked';

// Release notes stay in the same file used by the plugin's release process.
const notes = changelog.replace(/^\[[^\]]+\]:[^\n]*$/gm, '');
const headings = [...notes.matchAll(/^## \[([^\]]+)\](?: - (\d{4}-\d{2}-\d{2}))?\s*$/gm)];
export const releases = headings.map((heading, index) => {
  const version = heading[1];
  const body = notes.slice(heading.index! + heading[0].length, headings[index + 1]?.index ?? notes.length).trim();
  return {
    version, date: heading[2], slug: version.toLowerCase(),
    released: version !== 'Unreleased',
    html: marked.parse(body, { async: false }),
    github: version === 'Unreleased' ? null : `https://github.com/silverfoxy/decktation/releases/tag/v${version}`,
  };
});
export type Release = typeof releases[number];
