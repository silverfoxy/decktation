const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const {createRequire}=require('node:module');
const ts=require('typescript');
const source=path.resolve(__dirname,'../src/i18n.ts');
function load(saved, language='en-US', blocked=false, steam){
 const values=new Map(saved?[['decktation.interfaceLanguage',saved]]:[]);
 const storage={getItem:key=>{if(blocked)throw Error('blocked');return values.get(key);},setItem:(key,v)=>{if(blocked)throw Error('blocked');values.set(key,v);}};
 const exports={};
 vm.runInNewContext(ts.transpileModule(fs.readFileSync(source,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText,{exports,require:createRequire(source),window:{localStorage:storage,SteamClient:steam},navigator:{language},Intl,setTimeout,clearTimeout});
 return {api:exports,values};
}
test('catalog coverage and placeholders match',()=>{
 const en=require('../src/locales/en.json');
 for(const lang of ['es','ru','pt','pl','ko','ja','de','fr','zh']) {
 const es=require('../src/locales/'+lang+'.json');
 assert.deepEqual(Object.keys(es).sort(),Object.keys(en).sort());
 for(const key of Object.keys(en)){
  assert.ok(es[key].trim());
  assert.deepEqual((es[key].match(/\{\w+\}/g)||[]).sort(),(en[key].match(/\{\w+\}/g)||[]).sort(),key);
 }
 }
});
test('regional Spanish, English fallback and explicit preference',()=>{
 const {api,values}=load(null,'es-MX');
 assert.equal(api.t('Advanced settings'),'Ajustes avanzados');
 assert.equal(api.resolveLocale('auto','it-IT'),'en');
 api.setInterfacePreference('en');assert.equal(api.t('Back'),'Back');
 assert.equal(values.get('decktation.interfaceLanguage'),'en');
 assert.equal(load('es','en-US').api.t('Back'),'Volver');
 assert.equal(api.t('Custom profile'),'Custom profile');
});
test('safe storage, interpolation and dictation names',()=>{
 const {api}=load(null,'en',true);api.setInterfacePreference('es');
 assert.equal(api.t('Button {number}',{number:2}),'Botón 2');
 assert.equal(api.languageName('auto','Auto Detect'),'Detección automática');
 assert.equal(api.languageName('en','English'),'English');
 assert.equal(api.languageName('es','Spanish'),'Español');
 api.setInterfacePreference('ja');
 assert.equal(api.languageName('es','Spanish'),'Español');
 assert.equal(api.languageName('not_a_code','Original label'),'Original label');
});

test('Steam language overrides renderer locale but never explicit selection',async()=>{
 const {api}=load(null,'en-US',false,{Settings:{GetCurrentLanguage:async()=> 'spanish'}});
 await api.initializeSteamLanguage();assert.equal(api.t('Back'),'Volver');
 api.setInterfacePreference('en');assert.equal(api.t('Back'),'Back');
 assert.equal(api.resolveLocale('auto','latam'),'es');
 const failure=load(null,'es-ES',false,{Settings:{GetCurrentLanguage:async()=>{throw Error('unavailable');}}});
 await failure.api.initializeSteamLanguage();assert.equal(failure.api.t('Back'),'Volver');
});

test('all Steam language names map to an available catalog',()=>{
 const {api}=load();
 for(const [name,code] of Object.entries({english:'en',spanish:'es',latam:'es',russian:'ru',portuguese:'pt',brazilian:'pt',polish:'pl',koreana:'ko',japanese:'ja',german:'de',french:'fr',schinese:'zh',tchinese:'zh'})){
  assert.equal(api.resolveLocale('auto',name),code);
  api.setInterfacePreference(code);
  assert.ok(api.t('Mode'));
 }
});

test('every supported dictation code has a native display name',()=>{
 const source=fs.readFileSync(path.resolve(__dirname,'../src/index.tsx'),'utf8');
 const options=source.slice(source.indexOf('const WHISPER_LANGUAGE_OPTIONS'),source.indexOf('const MODEL_SIZE_OPTIONS'));
 const names=require('../src/locales/language-names.json');
 const codes=[...options.matchAll(/data: "([^"]+)", label:/g)].map(m=>m[1]).filter(x=>x!=='auto');
 assert.deepEqual(Object.keys(names).sort(),codes.sort());
 for(const value of Object.values(names))assert.ok(value.trim());
});

test('stable review controls use translations and preserve dynamic content',()=>{
 const source=fs.readFileSync(path.resolve(__dirname,'../src/index.tsx'),'utf8');
 for(const key of ['Review transcription','Transcription sending','Send immediately','Review before sending','Send after countdown','Press Enter yourself','Type into chat without submitting','Cancel']) {
  assert.ok(source.includes('t("'+key+'")'),key);
  for(const lang of ['en','es','ru','pt','pl','ko','ja','de','fr','zh']) assert.ok(require('../src/locales/'+lang+'.json')[key],lang+': '+key);
 }
 assert.ok(source.includes('{pendingDraft.text}'));
 const {api}=load('es');
 assert.equal(api.t('Review stays visible until you decide. Tap {binding} to send; hold it to cancel. Open Decktation to review longer text.',{binding:'L1+R1'}).includes('L1+R1'),true);
 assert.equal(api.t('“{text}” — open Decktation to review, send or cancel',{text:'Mañana 漢字'}).includes('Mañana 漢字'),true);
});
