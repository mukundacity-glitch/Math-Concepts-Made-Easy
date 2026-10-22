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

test('entrypoint registers a single isolated diagnostics composition', () => {
  assert.match(read('src/index.ts'), /registerRoot\(RemotionRoot\)/);
  const root = read('src/Root.tsx');
  assert.match(root, /id="ScaffoldDiagnostics"/);
  assert.match(root, /width=\{1920\}/);
  assert.match(root, /height=\{1080\}/);
  assert.match(root, /fps=\{30\}/);
  assert.match(root, /durationInFrames=\{30\}/);
  assert.doesNotMatch(root, /PremiumLesson|PremiumShort/);
});

test('scaffold does not access upload state, credentials or Python internals', () => {
  for (const filename of ['src/index.ts','src/Root.tsx','src/scaffold/ScaffoldDiagnostics.tsx']) {
    const source = read(filename);
    assert.doesNotMatch(source, /state\/progress|youtube|upload|child_process|autopilot\.py|YT_TOKEN_JSON/i);
  }
});

test('scaffold offers typecheck, studio and repeatable bundling commands', () => {
  for (const key of ['studio', 'typecheck', 'test', 'check', 'bundle']) {
    assert.equal(typeof pkg.scripts[key], 'string', key);
  }
  assert.match(read('README.md'), /Phase 4 Step 2/);
});
