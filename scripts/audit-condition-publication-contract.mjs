#!/usr/bin/env node

import { promises as fs } from 'node:fs';
import path from 'node:path';

const ROOT = process.cwd();
const CONDITIONS_ROOT = path.join(ROOT, 'special-needs', 'conditions');
const SITEMAP_PATH = path.join(ROOT, 'sitemap-special-needs.xml');
const PUBLIC_BASE = 'https://healthrenewal.org/';

const errors = [];
const notes = [];

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function walkIndexFiles(directory) {
  if (!(await exists(directory))) return [];
  const entries = await fs.readdir(directory, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...await walkIndexFiles(fullPath));
    } else if (entry.isFile() && entry.name === 'index.html') {
      files.push(fullPath);
    }
  }

  return files.sort();
}

function extractMeta(html, name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const patterns = [
    new RegExp(`<meta\\s+[^>]*name=["']${escaped}["'][^>]*content=["']([^"']*)["'][^>]*>`, 'i'),
    new RegExp(`<meta\\s+[^>]*content=["']([^"']*)["'][^>]*name=["']${escaped}["'][^>]*>`, 'i'),
  ];
  for (const pattern of patterns) {
    const match = html.match(pattern);
    if (match) return match[1].trim();
  }
  return '';
}

function extractCanonical(html) {
  const patterns = [
    /<link\s+[^>]*rel=["']canonical["'][^>]*href=["']([^"']+)["'][^>]*>/i,
    /<link\s+[^>]*href=["']([^"']+)["'][^>]*rel=["']canonical["'][^>]*>/i,
  ];
  for (const pattern of patterns) {
    const match = html.match(pattern);
    if (match) return match[1].trim();
  }
  return '';
}

function countH1(html) {
  return (html.match(/<h1\b/gi) || []).length;
}

function hasDraftMarkers(html) {
  return /name=["']pt-publication-status["'][^>]*content=["']draft-unpublished["']/i.test(html)
    && /data-publication-status=["']draft-unpublished["']/i.test(html);
}

function isStrictDraftRobots(robots) {
  const directives = new Set(robots.toLowerCase().split(',').map(value => value.trim()).filter(Boolean));
  return ['noindex', 'nofollow', 'noarchive', 'nosnippet'].every(value => directives.has(value));
}

function isIndexable(robots) {
  const value = robots.toLowerCase();
  return !value.includes('noindex');
}

function expectedPublicUrl(filePath) {
  const relativeDirectory = path.relative(ROOT, path.dirname(filePath)).split(path.sep).join('/');
  return `${PUBLIC_BASE}${relativeDirectory}/`;
}

const sitemapXml = await fs.readFile(SITEMAP_PATH, 'utf8');
const sitemapUrls = new Set([...sitemapXml.matchAll(/<loc>\s*([^<]+?)\s*<\/loc>/g)].map(match => match[1].trim()));
const pages = await walkIndexFiles(CONDITIONS_ROOT);

if (pages.length === 0) {
  notes.push('لا توجد صفحات حالات يدوية تحت special-needs/conditions في هذا الرأس.');
}

for (const filePath of pages) {
  const html = await fs.readFile(filePath, 'utf8');
  const relative = path.relative(ROOT, filePath).split(path.sep).join('/');
  const robots = extractMeta(html, 'robots');
  const canonical = extractCanonical(html);
  const expectedUrl = expectedPublicUrl(filePath);
  const listed = sitemapUrls.has(expectedUrl);
  const indexable = robots ? isIndexable(robots) : true;

  if (countH1(html) !== 1) {
    errors.push(`${relative}: يجب أن تحتوي الصفحة على H1 واحد فقط.`);
  }

  if (indexable) {
    if (!robots) errors.push(`${relative}: الصفحة القابلة للفهرسة لا تعلن meta robots صريحًا.`);
    if (!listed) errors.push(`${relative}: تعلن قابلية الفهرسة لكنها غير مسجلة في sitemap-special-needs.xml.`);
    if (hasDraftMarkers(html)) errors.push(`${relative}: صفحة قابلة للفهرسة ما تزال تحمل علامات draft-unpublished.`);
    if (canonical !== expectedUrl) {
      errors.push(`${relative}: canonical غير مطابق للمسار المنشور المتوقع (${expectedUrl}).`);
    }
    if (!/type=["']application\/ld\+json["']/i.test(html)) {
      errors.push(`${relative}: الصفحة المنشورة تفتقد JSON-LD ظاهرًا.`);
    }
    notes.push(`${relative}: منشورة تعاقديًا ومسجلة في الخريطة.`);
  } else {
    if (listed) errors.push(`${relative}: صفحة noindex لا يجوز إدراجها في sitemap-special-needs.xml.`);
    if (!isStrictDraftRobots(robots)) {
      errors.push(`${relative}: المسودة غير المسجلة يجب أن تستخدم noindex,nofollow,noarchive,nosnippet.`);
    }
    if (!hasDraftMarkers(html)) {
      errors.push(`${relative}: المسودة تحتاج pt-publication-status وdata-publication-status بقيمة draft-unpublished.`);
    }
    notes.push(`${relative}: مسودة معزولة عن الفهرسة والخريطة.`);
  }
}

console.log(`Condition publication contract: ${pages.length} page(s) checked.`);
for (const note of notes) console.log(`- ${note}`);

if (errors.length > 0) {
  console.error('\nPublication contract violations:');
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log('Condition publication contract passed.');
