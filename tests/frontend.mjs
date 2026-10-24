// Isolated DOM-contract tests for the real site script, without browser packages.
// Timing here measures handler CPU in this harness, not browser painting or FPS.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {performance} from 'node:perf_hooks';

const source = fs.readFileSync(new URL('../site/app.js', import.meta.url), 'utf8');
const translationSource = fs.readFileSync(new URL('../site/translations.js', import.meta.url), 'utf8');
const languageSource = fs.readFileSync(new URL('../site/i18n.js', import.meta.url), 'utf8');
const html = fs.readFileSync(new URL('../site/index.html', import.meta.url), 'utf8');
assert.ok(!html.includes('data-os="osx"'), 'macOS must be absent from the public platform selection');
const dictionaryContext = vm.createContext({});
vm.runInContext(translationSource, dictionaryContext);
const dictionaries = dictionaryContext.ReplantedMessages;
assert.deepEqual(Object.keys(dictionaries), ['de','en','fr','it','es']);
const placeholders = text => [...text.matchAll(/\{(\w+)\}/g)].map(m=>m[1]).sort();
for (const [language, messages] of Object.entries(dictionaries)) {
  assert.deepEqual(Object.keys(messages).sort(), Object.keys(dictionaries.de).sort(), language);
  for (const [key, text] of Object.entries(messages)) {
    assert.equal(typeof text, 'string');
    assert.ok(text.trim(), `${language}.${key}`);
    assert.deepEqual(placeholders(text),placeholders(dictionaries.de[key]),`${language}.${key}`);
  }
}
assert.ok(!languageSource.includes('innerHTML'), 'Translations must remain text, never executable markup');
class Element {
  constructor(dataset = {}) { this.dataset = dataset; this.attrs = {}; this.listeners = {}; this.children = []; this.textContent = ''; this.value = 'x64'; }
  setAttribute(key, value) { this.attrs[key] = value; }
  removeAttribute(key) { delete this.attrs[key]; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  replaceChildren() { this.children = []; this.textContent = ''; }
  append(child) { this.children.push(child); }
  set href(value) { this.attrs.href = value; }
}
async function boot(release, manifest, fail = false, options = {}) {
  const elements = Object.fromEntries(['release-status','architecture','launcher-download','launcher-meta','game-download','game-meta','all-releases','repository-link','language','language-picker'].map(id => [id,new Element()]));
  const buttons = [...html.matchAll(/data-os="([^"]+)"/g)].map(match => new Element({os:match[1]}));
  const translations = {};
  for (const [suffix, datasetKey] of [['','i18n'],['-aria','i18nAria'],['-alt','i18nAlt'],['-description','i18nDescription']]) {
    translations[`[data-i18n${suffix}]`] = [...html.matchAll(new RegExp(`data-i18n${suffix}="([^"]+)"`, 'g'))].map(match => {
      assert.ok(Object.hasOwn(dictionaries.de,match[1]),match[1]);
      return new Element({[datasetKey]:match[1]});
    });
  }
  const requests = [];
  const storage = options.storage || new Map();
  const location = {href:options.href || 'https://naroci.github.io/BeastsAndBumpkinsReplanted/', search:new URL(options.href || 'https://naroci.github.io/BeastsAndBumpkinsReplanted/').search};
  const document = {documentElement:{lang:'de'},getElementById:id=>elements[id],querySelectorAll:selector=>selector==='[data-os]'?buttons:translations[selector]||[],createElement:()=>new Element()};
  const context = vm.createContext({document,URL,URLSearchParams,location,
    history:{replaceState:(_,__,href)=>{location.href=href;location.search=new URL(href).search;}},
    localStorage:{getItem:key=>{if(options.blockStorage)throw Error('Denied');return storage.get(key)||null;},setItem:(key,value)=>{if(options.blockStorage)throw Error('Denied');storage.set(key,value);}},
    navigator:{platform:options.platform || 'Linux x86_64',languages:options.languages || ['de-DE']},fetch:async(path)=>{
    requests.push(path);
    if (fail) throw Error('Offline');
    return {ok:true,json:async()=>path==='release.json'?release:manifest};
  }});
  vm.runInContext(translationSource,context);
  vm.runInContext(languageSource,context);
  vm.runInContext(source,context);
  await new Promise(setImmediate);
  return {elements, buttons, requests, document, translations, storage, location, i18n:context.ReplantedI18n};
}
const repository = 'Naroci/BeastsAndBumpkinsReplanted';
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
for (const os of ['win','linux']) {
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
for (const language of ['de','en','fr','it','es']) {
  const localized=await boot(ready,manifest,false,{href:`https://naroci.github.io/BeastsAndBumpkinsReplanted/?lang=${language}`});
  assert.equal(localized.document.documentElement.lang,language);
  assert.equal(localized.document.title,dictionaries[language]['page.title']);
  assert.equal(localized.elements['release-status'].textContent,dictionaries[language]['status.ready'].replace('{tag}','v0.2.0').replace('{runtime}','linux-x64'));
  for(const el of localized.translations['[data-i18n]'])assert.equal(el.textContent,dictionaries[language][el.dataset.i18n]);
  for(const el of localized.translations['[data-i18n-aria]'])assert.equal(el.attrs['aria-label'],dictionaries[language][el.dataset.i18nAria]);
  for(const el of localized.translations['[data-i18n-alt]'])assert.equal(el.attrs.alt,dictionaries[language][el.dataset.i18nAlt]);
  for(const os of ['win','linux'])for(const arch of ['x64','arm64']) {
    localized.buttons.find(b=>b.dataset.os===os).listeners.click();
    localized.elements.architecture.value=arch;
    localized.elements.architecture.listeners.change();
    assert.equal(localized.elements['launcher-download'].attrs.href,os==='linux'&&arch==='x64'?pkg.url:undefined);
    if(os!=='linux'||arch!=='x64')assert.equal(localized.elements['launcher-meta'].textContent,dictionaries[language]['package.missing']);
  }
  assert.equal(localized.requests.length,2);
  const offline=await boot(ready,manifest,true,{href:`https://naroci.github.io/BeastsAndBumpkinsReplanted/?lang=${language}`});
  assert.equal(offline.elements['release-status'].textContent,dictionaries[language]['status.error']);
  const empty=await boot({repository,published:false},null,false,{href:`https://naroci.github.io/BeastsAndBumpkinsReplanted/?lang=${language}`});
  assert.equal(empty.elements['release-status'].textContent,dictionaries[language]['status.empty']);
}
const saved=new Map([['replanted.website.language','fr']]);
let languageState=await boot(ready,manifest,false,{storage:saved,languages:['it-IT']});
assert.equal(languageState.i18n.language,'fr','Saved selection precedes browser preference');
languageState=await boot(ready,manifest,false,{storage:saved,languages:['it-IT'],href:'https://example.org/site/?lang=es&other=1#downloads'});
assert.equal(languageState.i18n.language,'es','Explicit URL precedes saved selection');
languageState.elements.language.value='en';
languageState.elements.language.listeners.change();
assert.equal(saved.get('replanted.website.language'),'en');
assert.equal(languageState.location.href,'https://example.org/site/?lang=en&other=1#downloads');
assert.equal(languageState.elements['launcher-download'].attrs.href,pkg.url);
assert.equal(languageState.requests.length,2,'Language switch must not request metadata or packages again');
const reload=await boot(ready,manifest,false,{storage:saved,languages:['it-IT']});
assert.equal(reload.i18n.language,'en');
for(const [languages,expected] of [[['pt-BR','it-IT'],'it'],[['fr-CA'],'fr'],[['es-MX'],'es'],[['ja-JP'],'en']]) {
  assert.equal((await boot(ready,manifest,false,{languages})).i18n.language,expected);
}
languageState=await boot(ready,manifest,false,{blockStorage:true,href:'https://example.org/?lang=__proto__',languages:['it-IT']});
assert.equal(languageState.i18n.language,'it');
languageState.elements.language.value='es';languageState.elements.language.listeners.change();
assert.equal(languageState.i18n.language,'es','Storage denial must not prevent language selection');
const mac=await boot(ready,manifest,false,{platform:'MacIntel'});
assert.deepEqual(mac.buttons.map(button=>button.dataset.os),['win','linux']);
assert.equal(mac.buttons.find(button=>button.attrs['aria-pressed']==='true').dataset.os,'win');
assert.match(mac.elements['release-status'].textContent,/win-x64/);
const currentReady={repository,published:true,tag:'0.3.1 / 0.1.0',manifest:'launcher-updates.json'};
const currentManifest=JSON.parse(fs.readFileSync(new URL('../site/launcher-updates.json',import.meta.url),'utf8'));
const current=await boot(currentReady,currentManifest);
assert.deepEqual(current.requests,['release.json','launcher-updates.json']);
assert.equal(current.elements['launcher-download'].attrs.href,currentManifest.launcher.platforms['linux-x64'].url);
assert.equal(current.elements['game-download'].attrs.href,currentManifest.game.platforms['linux-x64'].url);
const initialManifest = structuredClone(currentManifest);
initialManifest.launcher.platforms['linux-x64'] = {...initialManifest.launcher.platforms['linux-x64'], url:`https://github.com/${repository}/releases/download/starter-build/launcher-setup.zip`, entryPoint:'bb-replanted.sh'};
const initial = await boot({...currentReady,manifest:'downloads.json'},initialManifest);
assert.deepEqual(initial.requests,['release.json','downloads.json']);
assert.equal(initial.elements['launcher-download'].attrs.href,initialManifest.launcher.platforms['linux-x64'].url);
assert.equal(initial.elements['game-download'].attrs.href,currentManifest.game.platforms['linux-x64'].url);
const setupSource=JSON.parse(fs.readFileSync(new URL('../site/launcher-downloads.json',import.meta.url),'utf8'));
const downloadCatalog={...currentManifest,launcher:setupSource.launcher};
const canonical=await boot({...currentReady,manifest:'launcher-downloads.json'},downloadCatalog);
assert.deepEqual(canonical.requests,['release.json','launcher-downloads.json']);
for(const language of ['de','en','fr','it','es']) {
  canonical.elements.language.value=language;canonical.elements.language.listeners.change();
  for(const os of ['win','linux'])for(const arch of ['x64','arm64']) {
    canonical.buttons.find(button=>button.dataset.os===os).listeners.click();
    canonical.elements.architecture.value=arch;canonical.elements.architecture.listeners.change();
    for(const component of ['launcher','game'])assert.equal(canonical.elements[`${component}-download`].attrs.href,downloadCatalog[component].platforms[`${os}-${arch}`]?.url);
  }
}
assert.equal(canonical.requests.length,2);
for(const language of ['de','en','fr','it','es']) {
  current.elements.language.value=language;current.elements.language.listeners.change();
  for(const os of ['win','linux'])for(const arch of ['x64','arm64']) {
    current.buttons.find(button=>button.dataset.os===os).listeners.click();
    current.elements.architecture.value=arch;current.elements.architecture.listeners.change();
    for(const component of ['launcher','game'])assert.equal(current.elements[`${component}-download`].attrs.href,currentManifest[component].platforms[`${os}-${arch}`]?.url);
  }
}
assert.equal(current.requests.length,2);
for(const url of [undefined, 'javascript:alert(1)',`https://github.com/Other/Repo/releases/download/v1/a.zip`,`https://github.com/${repository}/releases/latest/download/a.zip`,`https://github.com/${repository}/releases/download/v1/a.zip?token=x`,`https://github.com/${repository}/releases/download/../a.zip`]) {
  const invalid=await boot(currentReady,{schemaVersion:2,launcher:{version:'1.0.0',platforms:{'linux-x64':{...pkg,url}}}});
  assert.equal(invalid.elements['launcher-download'].attrs.href,undefined);
}
const gated=await boot({...currentReady,published:false},currentManifest);
assert.deepEqual(gated.requests,['release.json']);
assert.equal(gated.elements['launcher-download'].attrs.href,undefined);
const stats = values => {
  values.sort((a,b)=>a-b);
  return Object.fromEntries([['p50',.5],['p95',.95],['p99',.99],['max',1]].map(([label,q])=>[label,Number(values[Math.min(values.length-1,Math.ceil(values.length*q)-1)].toFixed(6))]));
};
const samples=[],batches=[],languageSamples=[];
for(let i=0;i<2000;i++) {
  const start=performance.now();
  state.buttons[i%state.buttons.length].listeners.click();
  samples.push(performance.now()-start);
}
for(let i=0;i<200;i++) {
  const start=performance.now();
  for(let j=0;j<32;j++) {
    state.buttons[(i+j)%state.buttons.length].listeners.click();
    state.elements.architecture.value=j%2?'x64':'arm64';
    state.elements.architecture.listeners.change();
  }
  batches.push(performance.now()-start);
}
assert.equal(state.requests.length,2);
for(let i=0;i<500;i++) {
  const start=performance.now();
  state.elements.language.value=['de','en','fr','it','es'][i%5];
  state.elements.language.listeners.change();
  languageSamples.push(performance.now()-start);
}
assert.equal(state.requests.length,2);
console.log(JSON.stringify({passed:true,languages:Object.keys(dictionaries),keysPerLanguage:Object.keys(dictionaries.de).length,coverage:'five languages × four visible platform/architecture combinations; macOS absent and Mac host fallback; existing schema-2 manifest with different release tags; publication gate; unsafe URLs rejected; language persistence; no extra per-selection fetches',timingScope:'Node VM handler CPU; excludes browser layout/paint and protocol latency',singleMs:stats(samples),batch64Ms:stats(batches),languageSwitchMs:stats(languageSamples),networkRequests:state.requests.length},null,2));
