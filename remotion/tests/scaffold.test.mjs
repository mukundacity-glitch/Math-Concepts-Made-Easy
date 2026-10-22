import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import test from 'node:test';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (relative) => readFileSync(join(ROOT, relative), 'utf8');
const pkg = JSON.parse(read('package.json'));

test('Remotion packages are pinned to the same exact compatible version', () => {
  assert.equal(pkg.private, true);
  assert.equal(pkg.dependencies.remotion, pkg.devDependencies['@remotion/cli']);
  assert.match(pkg.dependencies.remotion, /^\d+\.\d+\.\d+$/);
  assert.equal(pkg.dependencies.react, pkg.dependencies['react-dom']);
});

test('entrypoint registers diagnostics and one isolated premium lesson composition', () => {
  assert.match(read('src/index.ts'), /registerRoot\(RemotionRoot\)/);
  const root = read('src/Root.tsx');
  assert.match(root, /id="ScaffoldDiagnostics"/);
  assert.match(root, /id="PremiumLesson"/);
  assert.match(root, /calculateMetadata=/);
  assert.match(root, /width=\{lessonCanvas\.width\}/);
  assert.match(root, /height=\{lessonCanvas\.height\}/);
  assert.doesNotMatch(root, /id="PremiumShort"/);
});

test('scaffold remains isolated from uploader, credentials and production state', () => {
  for (const filename of ['src/index.ts','src/Root.tsx','src/scaffold/ScaffoldDiagnostics.tsx']) {
    const source = read(filename);
    assert.doesNotMatch(source, /state\/progress|youtube|child_process|autopilot\.py|YT_TOKEN_JSON/i);
  }
});

test('scaffold exposes typecheck, studio, tests and bundling', () => {
  for (const key of ['studio', 'typecheck', 'test', 'check', 'bundle']) {
    assert.equal(typeof pkg.scripts[key], 'string', key);
  }
  assert.match(read('README.md'), /Phase 4.*Step 3/);
});
