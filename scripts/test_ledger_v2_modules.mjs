// Compile the actual UI modules as ES modules: node --check alone missed
// malformed template expressions under Node 24's format auto-detection.
// Run: node --experimental-vm-modules scripts/test_ledger_v2_modules.mjs
import {readFileSync} from 'node:fs';
import {SourceTextModule, Script} from 'node:vm';
for (const name of ['app.js','model.js']) {
  new SourceTextModule(readFileSync(new URL('../portal/ledger-v2/'+name, import.meta.url),'utf8'));
}
new Script(readFileSync(new URL('../portal/ledger-v2/sw.js', import.meta.url),'utf8'));
console.log('ledger-v2 real UI module compilation: OK');
