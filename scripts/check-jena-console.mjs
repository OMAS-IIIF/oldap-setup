/** Live acceptance of the unmodified Apache Fuseki UI and native protocols.
 * Usage: node scripts/check-jena-console.mjs PRIVATE_JSON RESULT_DIR FUSEKI_JAR [ORIGIN]
 * Credentials stay in memory. Writes use a unique disposable graph, always cleaned up.
 */
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {createHash, randomUUID} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
const require = createRequire(new URL('../../oldap-app/package.json', import.meta.url));
const {chromium} = require('@playwright/test');
const [credentialFile, directory, fusekiJar, origin = 'https://fuseki.home.org'] = process.argv.slice(2);
if (!credentialFile || !directory || !fusekiJar || origin !== 'https://fuseki.home.org') throw Error('Explicit home credentials, results and reviewed Fuseki JAR required.');
if ((fs.statSync(credentialFile).mode & 0o077) !== 0) throw Error('Credential file must be private.');
const credentials = JSON.parse(fs.readFileSync(credentialFile, 'utf8'));
fs.mkdirSync(directory, {recursive: true});
const nativeIndex = execFileSync('python3', ['-c', 'import zipfile,sys; sys.stdout.buffer.write(zipfile.ZipFile(sys.argv[1]).read("webapp/index.html"))', fusekiJar]);
const browser = await chromium.launch({args: ['--no-proxy-server']});
const graph = 'urn:oldap:console-check:' + randomUUID();
const checks = [];
let context;
const headers = {Origin: origin};
async function update(text) {
  const r = await context.request.post(origin + '/oldap/update', {headers: {...headers, 'Content-Type': 'application/sparql-update'}, data: text});
  if (![200,204].includes(r.status())) throw Error('Native update status ' + r.status());
}
async function query(text) {
  const r = await context.request.post(origin + '/oldap/query', {headers: {...headers, 'Content-Type': 'application/sparql-query', Accept: 'application/sparql-results+json'}, data: text});
  if (r.status() !== 200) throw Error('Native query status ' + r.status());
  return r.json();
}
try {
  context = await browser.newContext({httpCredentials: credentials});
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const response = await page.goto(origin, {waitUntil: 'networkidle'});
  if (response.status() !== 200) throw Error('Administrator page status ' + response.status());
  if (!(await response.body()).equals(nativeIndex)) throw Error('Page differs from pinned Apache distribution.');
  checks.push({name: 'Unmodified official Apache index', sha256: createHash('sha256').update(nativeIndex).digest('hex')});
  await page.getByText('Apache Jena Fuseki', {exact: false}).first().waitFor();
  await page.screenshot({path: path.join(directory, 'fuseki-home.png'), fullPage: true});
  const server = await context.request.get(origin + '/$/server');
  const info = await server.json();
  if (info.version !== '6.2.0' || !info.datasets.some(d => d['ds.name'] === '/oldap')) throw Error('Native dataset registration missing.');
  checks.push({name: 'Native server and dataset discovery', version: info.version, dataset: '/oldap'});
  const graphs = await query('SELECT DISTINCT ?g { GRAPH ?g { ?s ?p ?o } } ORDER BY ?g');
  checks.push({name: 'Live graph inventory', rows: graphs.results.bindings.length});
  // Use the actual editor and native query button, not just HTTP smoke checks.
  await page.goto(origin + '/#/dataset/oldap/query', {waitUntil: 'networkidle'});
  await page.locator('.CodeMirror').first().waitFor();
  await page.locator('.CodeMirror').first().evaluate(el => el.CodeMirror.setValue('SELECT DISTINCT ?graph WHERE { GRAPH ?graph { ?s ?p ?o } } ORDER BY ?graph LIMIT 100'));
  const [resultResponse] = await Promise.all([
    page.waitForResponse(r => /\/oldap\/(query|sparql)/.test(r.url()) && r.status() === 200),
    page.getByTitle('Run query', {exact: true}).click()
  ]);
  const result = await resultResponse.json();
  if (!result.results.bindings.length) throw Error('Browser query returned no graphs.');
  await page.screenshot({path: path.join(directory, 'fuseki-query.png'), fullPage: true});
  checks.push({name: 'Official browser query editor', rows: result.results.bindings.length});
  await update(`INSERT DATA { GRAPH <${graph}> { <urn:console-check:item> <urn:value> "temporary" } }`);
  if (!(await query(`ASK { GRAPH <${graph}> { <urn:console-check:item> <urn:value> "temporary" } }`)).boolean) throw Error('Native write/read failed.');
  checks.push({name: 'Native SPARQL update and readback', passed: true});
  const upload = await context.request.post(origin + '/oldap/data?graph=' + encodeURIComponent(graph), {headers: {...headers, 'Content-Type':'text/turtle'}, data:'<urn:console-check:upload> <urn:value> "uploaded" .'});
  if (![200,201,204].includes(upload.status()) || !(await query(`ASK { GRAPH <${graph}> { <urn:console-check:upload> ?p ?o } }`)).boolean) throw Error('Native upload failed.');
  checks.push({name: 'Native Graph Store upload and readback', passed: true});
  await page.getByRole('link', {name: 'add data'}).click();
  await page.locator('#dataset-graph-name').fill(graph);
  await page.locator('#file').setInputFiles({name:'console-check.ttl',mimeType:'text/turtle',buffer:Buffer.from('<urn:console-check:browser-upload> <urn:value> "browser" .')});
  const [uploadResponse] = await Promise.all([
    page.waitForResponse(r => r.url().includes('/oldap/') && r.request().method() === 'POST'),
    page.getByRole('button', {name:'upload now'}).click()
  ]);
  if (![200,201,204].includes(uploadResponse.status()) || !(await query(`ASK { GRAPH <${graph}> { <urn:console-check:browser-upload> ?p ?o } }`)).boolean) throw Error('Official browser upload failed.');
  checks.push({name:'Official browser file upload',passed:true});
  if ((await query('SELECT ?t { BIND(<<( <urn:s> <urn:p> <urn:o> )>> AS ?t) }')).results.bindings[0].t.type !== 'triple') throw Error('RDF 1.2 failed.');
  checks.push({name: 'RDF 1.2 triple terms', passed: true});
  const wrongOrigin = await context.request.post(origin + '/oldap/update', {headers:{Origin:'https://evil.example','Content-Type':'application/sparql-update'},data:`CLEAR GRAPH <${graph}>`});
  if (wrongOrigin.status() !== 403) throw Error('Cross-origin write accepted.');
  const lifecycle = await context.request.delete(origin + '/$/datasets/oldap', {headers});
  if (lifecycle.status() !== 403) throw Error('Dataset lifecycle not protected.');
  checks.push({name: 'Origin and dataset lifecycle barriers', passed:true});
  for (const route of ['/tx/bootstrap','/tx/BEGIN/00000000-0000-0000-0000-000000000000','/health']) {
    if ((await context.request.get(origin + route)).status() !== 404) throw Error('Private route exposed: ' + route);
  }
  const anonymous = await browser.newContext();
  for (const route of ['/','/$/server','/oldap/query','/oldap/update']) {
    if ((await anonymous.request.get(origin + route)).status() !== 401) throw Error('Anonymous access: ' + route);
  }
  checks.push({name:'Authentication and private endpoint isolation',passed:true});
  if (errors.length) throw Error('Browser JavaScript errors: ' + errors.join('; '));
  checks.push({name:'Browser JavaScript errors',count:0});
} finally {
  try {
    if (context) {
      await update(`DROP SILENT GRAPH <${graph}>`);
      if ((await query(`ASK { GRAPH <${graph}> { ?s ?p ?o } }`)).boolean) throw Error('Test graph cleanup failed.');
      checks.push({name:'Disposable test graph removed',passed:true});
    }
  } finally { await browser.close(); }
}
fs.writeFileSync(path.join(directory,'browser-results.json'),JSON.stringify({origin,checks},null,2)+'\n');
console.log(JSON.stringify({origin,checks},null,2));
