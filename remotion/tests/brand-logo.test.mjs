import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import test from 'node:test';

const path = 'public/branding/math-concepts-made-easy-logo.webp';
const sha256 = '466db2f838a17ef9978ccf79bd0459622bf20704904e0f2db0c52d28fe9c61f0';

test('canonical Math Concepts logo is a permanently tracked, intact WebP', () => {
  const logo = readFileSync(path);
  assert.equal(logo.subarray(0,4).toString(), 'RIFF');
  assert.equal(logo.subarray(8,12).toString(), 'WEBP');
  assert.equal(createHash('sha256').update(logo).digest('hex'), sha256);
});

test('every current slide uses the shared real logo component', () => {
  const read = (s) => readFileSync(s,'utf8');
  const header = read('src/components/BrandHeader.tsx');
  const brand = read('src/components/BrandLogo.tsx');
  const diag = read('src/scaffold/ScaffoldDiagnostics.tsx');
  assert.match(brand, /staticFile\(BRAND_LOGO_ASSET\)/);
  assert.match(header, /<BrandLogo size=\{72\}\s*\/>/);
  assert.match(diag, /<BrandLogo size=\{72\}\s*\/>/);
  assert.match(read('src/inverse/visuals.tsx'), /branding\/math-concepts-made-easy-logo\.webp/);
  for (const page of ['TitleCard', 'OutroCard']) {
    assert.match(read('src/components/'+page+'.tsx'), /<BrandHeader/);
  }
});
