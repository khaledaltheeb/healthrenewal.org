#!/usr/bin/env node

import { promises as fs } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const REPORT_DIR = path.join(ROOT, 'artifacts', 'accessibility-idrefs');
const JSON_REPORT = path.join(REPORT_DIR, 'report.json');
const MARKDOWN_REPORT = path.join(REPORT_DIR, 'report.md');
const STRICT = process.argv.includes('--strict');

const EXCLUDED_DIRS = new Set([
  '.git',
  '.github',
  'node_modules',
  'vendor',
  'artifacts',
  'coverage',
  'dist',
  'build'
]);

const IDREF_ATTRIBUTES = [
  'aria-activedescendant',
  'aria-controls',
  'aria-describedby',
  'aria-details',
  'aria-errormessage',
  'aria-flowto',
  'aria-labelledby',
  'aria-owns',
  'for',
  'headers',
  'list'
];

const SINGLE_IDREF_ATTRIBUTES = new Set([
  'aria-activedescendant',
  'aria-details',
  'aria-errormessage',
  'for',
  'list'
]);

function lineNumber(content, index) {
  return content.slice(0, index).split('\n').length;
}

function decodeHtml(value) {
  return value
    .replaceAll('&quot;', '"')
    .replaceAll('&#34;', '"')
    .replaceAll('&#39;', "'")
    .replaceAll('&apos;', "'")
    .replaceAll('&amp;', '&')
    .replaceAll('&lt;', '<')
    .replaceAll('&gt;', '>');
}

function getAttribute(tag, name) {
  const pattern = new RegExp(`(?:^|\\s)${name}\\s*=\\s*(?:"([^"]*)"|'([^']*)'|([^\\s>]+))`, 'i');
  const match = tag.match(pattern);
  return match ? decodeHtml(match[1] ?? match[2] ?? match[3] ?? '') : null;
}

async function collectHtmlFiles(directory) {
  const files = [];
  const entries = await fs.readdir(directory, { withFileTypes: true });

  for (const entry of entries) {
    if (entry.name.startsWith('.') && entry.name !== '.well-known') continue;
    if (EXCLUDED_DIRS.has(entry.name)) continue;

    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...await collectHtmlFiles(absolute));
    } else if (entry.isFile() && entry.name.toLowerCase().endsWith('.html')) {
      files.push(absolute);
    }
  }

  return files;
}

function addIssue(issues, issue) {
  issues.push({ severity: 'error', ...issue });
}

function inspectHtml(file, content) {
  const relativeFile = path.relative(ROOT, file).split(path.sep).join('/');
  const issues = [];
  const ids = new Map();
  const tags = [];
  const tagPattern = /<([a-zA-Z][\w:-]*)(?:\s[^<>]*?)?>/g;

  for (const match of content.matchAll(tagPattern)) {
    const tag = match[0];
    if (tag.startsWith('</') || tag.startsWith('<!')) continue;

    const tagName = match[1].toLowerCase();
    const index = match.index ?? 0;
    const line = lineNumber(content, index);
    const id = getAttribute(tag, 'id');

    tags.push({ tag, tagName, line });

    if (id !== null) {
      const normalizedId = id.trim();
      if (!normalizedId) {
        addIssue(issues, {
          code: 'empty-id',
          file: relativeFile,
          line,
          message: 'عنصر يحتوي على id فارغ.'
        });
      } else if (ids.has(normalizedId)) {
        addIssue(issues, {
          code: 'duplicate-id',
          file: relativeFile,
          line,
          target: normalizedId,
          message: `المعرّف "${normalizedId}" مكرر؛ ظهر أول مرة في السطر ${ids.get(normalizedId)}.`
        });
      } else {
        ids.set(normalizedId, line);
      }
    }
  }

  for (const { tag, tagName, line } of tags) {
    for (const attribute of IDREF_ATTRIBUTES) {
      const rawValue = getAttribute(tag, attribute);
      if (rawValue === null) continue;

      const targets = rawValue.trim().split(/\s+/).filter(Boolean);
      if (targets.length === 0) {
        addIssue(issues, {
          code: 'empty-idref',
          file: relativeFile,
          line,
          attribute,
          message: `السمة ${attribute} موجودة دون هدف.`
        });
        continue;
      }

      if (SINGLE_IDREF_ATTRIBUTES.has(attribute) && targets.length > 1) {
        addIssue(issues, {
          code: 'multiple-single-idref',
          file: relativeFile,
          line,
          attribute,
          target: rawValue,
          message: `السمة ${attribute} تقبل معرّفًا واحدًا في هذا الفحص، لكنها تشير إلى عدة قيم.`
        });
      }

      for (const target of targets) {
        if (!ids.has(target)) {
          addIssue(issues, {
            code: 'missing-idref-target',
            file: relativeFile,
            line,
            attribute,
            target,
            message: `السمة ${attribute} تشير إلى المعرّف غير الموجود "${target}".`
          });
        }
      }
    }

    if (tagName === 'a') {
      const href = getAttribute(tag, 'href');
      if (href?.startsWith('#') && href.length > 1) {
        let fragment = href.slice(1);
        try {
          fragment = decodeURIComponent(fragment);
        } catch {
          addIssue(issues, {
            code: 'invalid-fragment-encoding',
            file: relativeFile,
            line,
            target: fragment,
            message: `الرابط الداخلي يحتوي على ترميز fragment غير صالح: "${fragment}".`
          });
          continue;
        }

        if (!ids.has(fragment)) {
          addIssue(issues, {
            code: 'missing-fragment-target',
            file: relativeFile,
            line,
            target: fragment,
            message: `الرابط الداخلي يشير إلى المعرّف غير الموجود "${fragment}".`
          });
        }
      }
    }
  }

  return { relativeFile, ids: ids.size, issues };
}

function markdownEscape(value) {
  return String(value ?? '').replaceAll('|', '\\|').replaceAll('\n', ' ');
}

async function main() {
  const files = (await collectHtmlFiles(ROOT)).sort();
  const results = [];

  for (const file of files) {
    const content = await fs.readFile(file, 'utf8');
    results.push(inspectHtml(file, content));
  }

  const issues = results.flatMap((result) => result.issues);
  const affectedFiles = new Set(issues.map((issue) => issue.file));
  const byCode = Object.fromEntries(
    [...new Set(issues.map((issue) => issue.code))]
      .sort()
      .map((code) => [code, issues.filter((issue) => issue.code === code).length])
  );

  const report = {
    generatedAt: new Date().toISOString(),
    strict: STRICT,
    scannedHtmlFiles: files.length,
    affectedFiles: affectedFiles.size,
    issueCount: issues.length,
    byCode,
    issues
  };

  await fs.mkdir(REPORT_DIR, { recursive: true });
  await fs.writeFile(JSON_REPORT, `${JSON.stringify(report, null, 2)}\n`, 'utf8');

  const markdown = [
    '# تقرير سلامة معرّفات HTML والإحالات الدلالية',
    '',
    `- ملفات HTML المفحوصة: **${files.length}**`,
    `- الملفات المتأثرة: **${affectedFiles.size}**`,
    `- المشكلات: **${issues.length}**`,
    `- الوضع الصارم: **${STRICT ? 'مفعّل' : 'غير مفعّل'}**`,
    '',
    '## الملخص حسب النوع',
    '',
    ...(Object.keys(byCode).length
      ? Object.entries(byCode).map(([code, count]) => `- \`${code}\`: ${count}`)
      : ['- لم تُكتشف مشكلات.']),
    '',
    '## التفاصيل',
    '',
    ...(issues.length
      ? [
          '| الملف | السطر | النوع | السمة/الهدف | الوصف |',
          '|---|---:|---|---|---|',
          ...issues.map((issue) => `| ${markdownEscape(issue.file)} | ${issue.line} | \`${issue.code}\` | ${markdownEscape(issue.attribute ?? issue.target ?? '')} | ${markdownEscape(issue.message)} |`)
        ]
      : ['لا توجد مشكلات.']),
    ''
  ].join('\n');

  await fs.writeFile(MARKDOWN_REPORT, markdown, 'utf8');

  console.log(`Scanned ${files.length} HTML files; found ${issues.length} issue(s) in ${affectedFiles.size} file(s).`);
  console.log(`JSON report: ${path.relative(ROOT, JSON_REPORT)}`);
  console.log(`Markdown report: ${path.relative(ROOT, MARKDOWN_REPORT)}`);

  if (STRICT && issues.length > 0) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 2;
});
