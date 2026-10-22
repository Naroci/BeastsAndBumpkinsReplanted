// Isolated DOM-contract tests for the real site script, without browser packages.
// Timing here measures handler CPU in this harness, not browser painting or FPS.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {performance} from 'node:perf_hooks';

const source = fs.readFileSync(new URL('../site/app.js', import.meta.url), 'utf8');
class Element {
  constructor(dataset = {}) { this.dataset = dataset; this.attrs = {}; this.listeners = {}; this.children = []; this.textContent = ''; this.value = 'x64'; }
  setAttribute(key, value) { this.attrs[key] = value; }
  removeAttribute(key) { delete this.attrs[key]; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  replaceChildren() { this.children = []; this.textContent = ''; }
  append(child) { this.children.push(child); }
  set href(value) { this.attrs.href = value; }
}
async function boot(release, manifest, fail = false) {
  const elements = Object.fromEntries(['release-status','architecture','launcher-download','launcher-meta','game-download','game-meta','all-releases','repository-link'].map(id => [id,new Element()]));
  const buttons = ['win','linux','osx'].map(os => new Element({os}));
  const requests = [];
  const document = {getElementById:id=>elements[id],querySelectorAll:()=>buttons,createElement:()=>new Element()};
  vm.runInNewContext(source, {document,navigator:{platform:'Linux x86_64'},fetch:async(path)=>{
    requests.push(path);
    if (fail) throw Error('Offline');
    return {ok:true,json:async()=>path==='release.json'?release:manifest};
  }});
  await new Promise(setImmediate);
  return {elements, buttons, requests};
}
const repository = 'Naroci/BeastsAndBumpkinsPublic';
const ready = {repository,published:true,tag:'v0.2.0',manifest:'updates.json'};
const pkg = {url:`https://github.com/${repository}/releases/download/v0.2.0/launcher-linux-x64.zip`,sha256:'a'.repeat(64),size:123456,entryPoint:'replanted-launcher'};
const manifest = {schemaVersion:1,launcher:{version:'0.2.0',platforms:{'linux-x64':pkg}}};
let state = await boot({repository,published:false});
assert.deepEqual(state.requests,['release.json']);
assert.equal(state.elements['launcher-download'].attrs.href,undefined);
assert.match(state.elements['release-status'].textContent,/Noch kein Download/);
state = await boot(ready,manifest,true);
assert.match(state.elements['release-status'].textContent,/nicht erreichbar/);
assert.equal(state.elements['game-download'].attrs.href,undefined);
state = await boot(ready,manifest);
assert.deepEqual(state.requests,['release.json','updates.json']);
assert.equal(state.elements['launcher-download'].attrs.href,pkg.url);
assert.equal(state.elements['game-download'].attrs.href,undefined);
assert.equal(state.elements['launcher-meta'].children[0].textContent,`SHA-256: ${pkg.sha256}`);
for (const os of ['win','linux','osx']) {
  for (const arch of ['x64','arm64']) {
    state.buttons.find(b=>b.dataset.os===os).listeners.click();
    state.elements.architecture.value=arch;
    state.elements.architecture.listeners.change();
    assert.equal(state.elements['launcher-download'].attrs.href,os==='linux'&&arch==='x64'?pkg.url:undefined);
    assert.equal(state.buttons.filter(b=>b.attrs['aria-pressed']==='true').length,1);
  }
}
for (const bad of [{...pkg,url:'https://untrusted.example/file.zip'},{...pkg,sha256:'bad'},{...pkg,size:NaN}]) {
  const invalid=await boot(ready,{schemaVersion:1,launcher:{version:'0.2.0',platforms:{'linux-x64':bad}}});
  assert.equal(invalid.elements['launcher-download'].attrs.href,undefined);
}
assert.equal(state.requests.length,2,'Switching platforms must not make additional network requests');
assert.ok(state.buttons.every(b=>Object.keys(b.listeners).join()==='click'),'No pointer-move handler');
const stats = values => {
  values.sort((a,b)=>a-b);
  return Object.fromEntries([['p50',.5],['p95',.95],['p99',.99],['max',1]].map(([label,q])=>[label,Number(values[Math.min(values.length-1,Math.ceil(values.length*q)-1)].toFixed(6))]));
};
const samples=[],batches=[];
for(let i=0;i<2000;i++) {
  const start=performance.now();
  state.buttons[i%3].listeners.click();
  samples.push(performance.now()-start);
}
for(let i=0;i<200;i++) {
  const start=performance.now();
  for(let j=0;j<32;j++) {
    state.buttons[(i+j)%3].listeners.click();
    state.elements.architecture.value=j%2?'x64':'arm64';
    state.elements.architecture.listeners.change();
  }
  batches.push(performance.now()-start);
}
assert.equal(state.requests.length,2);
console.log(JSON.stringify({passed:true,coverage:'no-release, offline, all six platform selections, immutable URLs, hashes, unsafe links, missing components, no per-selection fetches',timingScope:'Node VM handler CPU; excludes browser layout/paint and protocol latency',singleMs:stats(samples),batch64Ms:stats(batches),networkRequests:state.requests.length},null,2));
