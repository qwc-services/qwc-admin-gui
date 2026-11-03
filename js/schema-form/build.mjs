// Build src/static/js/schema-form.min.js, with a banner listing the bundled packages and their licenses.
// Run in js/schema-form: npm ci && npm run build
import { build } from 'esbuild';
import { readFileSync } from 'node:fs';

const outfile = '../../src/static/js/schema-form.min.js';
const options = {
  entryPoints: ['entry.jsx'],
  bundle: true,
  minify: true,
  format: 'iife',
  globalName: 'SchemaForm',
  target: 'es2020',
  legalComments: 'eof',
  jsx: 'automatic',
  define: { 'process.env.NODE_ENV': '"production"' },
  outfile
};

const { metafile } = await build({ ...options, write: false, metafile: true });
// package directories of the bundled files, nested node_modules included
const packages = new Set(
  Object.keys(metafile.inputs)
    .map((input) => input.match(/^.*node_modules\/(?:@[^/]+\/)?[^/]+/)?.[0])
    .filter(Boolean)
);
const lines = [...new Set([...packages].map((dir) => {
  const pkg = JSON.parse(readFileSync(`${dir}/package.json`, 'utf8'));
  return ` * ${pkg.name} ${pkg.version} (${pkg.license})`;
}))].sort();
const banner = `/*! schema-form.min.js, built from js/schema-form in qwc-admin-gui. Bundled packages:\n${lines.join('\n')}\n */`;

await build({ ...options, banner: { js: banner } });
console.log(`Wrote ${outfile} (${packages.size} packages)`);
