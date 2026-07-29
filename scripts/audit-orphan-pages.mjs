#!/usr/bin/env node

import { promises as fs } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const STRICT = process.argv.includes('--strict');
const REPORT_DIR = path.join(ROOT, 'artifacts');
const SKIP_DIRS = new Set(['.git', '.github', 'node_modules', 'artifacts', 'vendor']);
const SKIP_FILES = new Set(['404.html']);

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    if (entry.name.startsWith('.') && entry.name !== '.well-known') continue;
    if (SKIP_DIRS.has(entry.name)) continue;

    const absolute = path.join(dir, entry.name);
    if (entry.isDirectory()) files.push(...await walk(absolute));
    else if (entry.isFile() && entry.name.endsWith('.html') && !SKIP_FILES.has(entry.name)) files.push(absolute);
  }

  return files;
}

function toPosix(value) {
  return value.split(path.sep).join('/');
}

function canonicalPagePath(file) {
  const relative = toPosix(path.relative(ROOT, file));
  if (relative === 'index.html') return '/';
  if (relative.endsWith('/index.html')) return `/${relative.slice(0, -'index.html'.length)}`;
  return `/${relative}`;
}

function normalizeInternalHref(href, sourcePage) {
  if (!href) return null;
  const trimmed = href.trim();
  if (!trimmed || trimmed.startsWith('#')) return null;
  if (/^(mailto:|tel:|javascript:|data:)/i.test(trimmed)) return null;

  try {
    const sourceUrl = new URL(sourcePage, 'https://example.invalid');
    const resolved = new URL(trimmed, sourceUrl);
    if (resolved.origin !== 'https://example.invalid') return null;

    let pathname = decodeURI(resolved.pathname).replace(/\/+/g, '/');
    if (pathname.endsWith('/index.html')) pathname = pathname.slice(0, -'index.html'.length);
    if (!path.extname(pathname) && !pathname.endsWith('/')) pathname += '/';
    return pathname || '/';
  } catch {
    return null;
  }
}

function extractLinks(html, sourcePage) {
  const links = new Set();
  const pattern = /<a\b[^>]*?\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi;
  let match;

  while ((match = pattern.exec(html)) !== null) {
    const normalized = normalizeInternalHref(match[1] ?? match[2] ?? match[3], sourcePage);
    if (normalized) links.add(normalized);
  }

  return [...links];
}

async function main() {
  const htmlFiles = await walk(ROOT);
  const pages = new Map();

  for (const file of htmlFiles) {
    const pagePath = canonicalPagePath(file);
    const html = await fs.readFile(file, 'utf8');
    pages.set(pagePath, { file: toPosix(path.relative(ROOT, file)), links: extractLinks(html, pagePath) });
  }

  const incoming = new Map([...pages.keys()].map((page) => [page, new Set()]));
  const brokenInternalTargets = [];

  for (const [source, data] of pages) {
    for (const target of data.links) {
      if (pages.has(target)) incoming.get(target).add(source);
      else if (target.endsWith('/') || target.endsWith('.html')) brokenInternalTargets.push({ source, target });
    }
  }

  const roots = ['/'].filter((page) => pages.has(page));
  const reachable = new Set(roots);
  const queue = [...roots];

  while (queue.length) {
    const source = queue.shift();
    for (const target of pages.get(source)?.links ?? []) {
      if (pages.has(target) && !reachable.has(target)) {
        reachable.add(target);
        queue.push(target);
      }
    }
  }

  const orphans = [...pages.keys()]
    .filter((page) => page !== '/' && !reachable.has(page))
    .sort((a, b) => a.localeCompare(b, 'ar'));

  const report = {
    generatedAt: new Date().toISOString(),
    totalHtmlPages: pages.size,
    reachablePages: reachable.size,
    orphanPages: orphans,
    brokenInternalTargets,
    incomingLinks: Object.fromEntries([...incoming].map(([page, sources]) => [page, [...sources].sort()])),
  };

  await fs.mkdir(REPORT_DIR, { recursive: true });
  await fs.writeFile(path.join(REPORT_DIR, 'orphan-pages.json'), `${JSON.stringify(report, null, 2)}\n`);

  const markdown = [
    '# Orphan page audit',
    '',
    `- HTML pages: ${report.totalHtmlPages}`,
    `- Reachable from home: ${report.reachablePages}`,
    `- Orphan candidates: ${orphans.length}`,
    `- Broken internal HTML targets: ${brokenInternalTargets.length}`,
    '',
    '## Orphan candidates',
    '',
    ...(orphans.length ? orphans.map((page) => `- \`${page}\``) : ['None.']),
    '',
    '## Broken internal HTML targets',
    '',
    ...(brokenInternalTargets.length
      ? brokenInternalTargets.map(({ source, target }) => `- \`${source}\` → \`${target}\``)
      : ['None.']),
    '',
  ].join('\n');

  await fs.writeFile(path.join(REPORT_DIR, 'orphan-pages.md'), markdown);

  console.log(markdown);

  if (STRICT && (orphans.length || brokenInternalTargets.length)) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
