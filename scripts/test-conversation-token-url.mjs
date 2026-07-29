import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../specialists-partners/assets/forms.js', import.meta.url), 'utf8');

assert.doesNotMatch(
  source,
  /portal\/\?conversation=.*token=/,
  'Conversation access tokens must not be generated in the URL query string.'
);

assert.match(
  source,
  /portal\/#conversation=.*token=/,
  'Conversation handoff must use the URL fragment so the token is not sent in HTTP requests or referrers.'
);

assert.match(
  source,
  /new URLSearchParams\(location\.hash\.replace\(\/\^#\//,
  'The portal must read credentials from the URL fragment.'
);

assert.match(
  source,
  /history\.replaceState\(null, document\.title, location\.pathname\)/,
  'The portal must remove credentials from the visible address immediately after reading them.'
);

assert.match(
  source,
  /link\.rel = 'noreferrer'/,
  'The generated portal link must explicitly suppress referrer data.'
);

console.log('Conversation token URL security checks passed.');
