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
test('compact controller debugger copy and live status labels are translated in all ten locales', () => {
 const keys = ['Held buttons', 'Source', 'Last transition', 'Pressed', 'Released', 'No buttons held',
  'No input yet', 'Live input unavailable', 'ms', 'Record up to 30 seconds of controller input.',
  'Press each paddle, then A. Do not type.',
  'Controller navigation is paused. Steam/Quick Access may open menus. Ends after 30 seconds; touch or mouse can stop early.',
  'Includes host/build details, controller interfaces and button transitions. Excludes typing, audio, transcripts, serials and input paths.',
  'Nothing is sent automatically. Send shares only this report with Sentry.',
  'Capture continues if you close this panel.', 'Report submitted. Event ID'];
 for (const lang of ['en','es','ru','pt','pl','ko','ja','de','fr','zh']) {
  const catalog = require('../src/locales/'+lang+'.json');
  for (const key of keys) {
   assert.ok(catalog[key]?.trim(), lang + ': ' + key);
   if (lang !== 'en' && !['Source', 'ms'].includes(key)) assert.notEqual(catalog[key], key, lang + ': untranslated ' + key);
  }
  assert.ok(!Object.keys(catalog).some(key => key.includes('delivery not confirmed')));
 }
});

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

test('updater messages translate backend errors and preserve release versions',()=>{
 const errors=['Could not check for updates.','The update could not be verified, so it was not installed.',"Decky's plugin installer is not available in this version. Update manually using the packaged Decktation ZIP.",'An update is already being prepared.','Wait for the transcription model to finish loading.','Finish the current dictation before updating.'];
 for(const lang of ['en','es','ru','pt','pl','ko','ja','de','fr','zh']) {
  const {api}=load(lang);
  const catalog=require('../src/locales/'+lang+'.json');
  for(const key of errors) assert.equal(api.t(key),catalog[key]);
  for(const key of ['Update to {version}','Version {version}','Update available: {version}']) {
   assert.ok(api.t(key,{version:'0.3.19'}).includes('0.3.19'));
   assert.ok(!api.t(key,{version:'0.3.19'}).includes('{version}'));
  }
 }
 const source=fs.readFileSync(path.resolve(__dirname,'../src/index.tsx'),'utf8');
 assert.ok(source.includes('setUpdateError(t(prepared.error ||'));
 assert.ok(source.includes('setUpdateError(t(result.error ||'));
});

test('visible JSX strings and literal translation keys are covered',()=>{
 const filename=path.resolve(__dirname,'../src/index.tsx');
 const source=fs.readFileSync(filename,'utf8');
 const ast=ts.createSourceFile(filename,source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 const en=require('../src/locales/en.json');
 function visit(node){
  if(ts.isJsxText(node)&&/[A-Za-z]/.test(node.getText(ast))) {
   assert.equal(node.getText(ast).trim(),'Decktation','Unlocalized JSX text: '+node.getText(ast).trim());
  }
  if(ts.isJsxAttribute(node)&&['title','label','menuLabel','description','aria-label'].includes(node.name.text)&&node.initializer&&ts.isStringLiteral(node.initializer)) {
   assert.equal(node.initializer.text,'Decktation','Unlocalized attribute: '+node.initializer.text);
  }
  if(ts.isCallExpression(node)&&node.expression.getText(ast)==='t'&&node.arguments[0]&&ts.isStringLiteral(node.arguments[0])) {
   assert.ok(Object.hasOwn(en,node.arguments[0].text),'Missing catalog key: '+node.arguments[0].text);
  }
  ts.forEachChild(node,visit);
 }
 visit(ast);
});

test('binding capture outcomes and English speech examples work in every locale',()=>{
 const outcomes=['Binding timed out. Your previous binding is unchanged.','Controller disconnected. Your previous binding is unchanged.','Use at most five buttons.','Finish recording before changing the binding.','Controller listener unavailable.','Binding session ended.'];
 const commandKey='Say command gg to enter /gg, or command ready for /ready. Use English or Auto Detect. Commands follow your sending settings.';
 const punctuationKey='With English or Auto Detect, say comma, period, or question mark to insert punctuation. Turn off to type these words literally.';
 for(const lang of ['en','es','ru','pt','pl','ko','ja','de','fr','zh']) {
  const {api}=load(lang),catalog=require('../src/locales/'+lang+'.json');
  assert.equal(api.t('Binding saved: {binding}',{binding:'L1 + B'}),catalog['Binding saved: {binding}'].replace('{binding}','L1 + B'));
  for(const key of outcomes)assert.equal(api.t(key),catalog[key]);
  for(const example of ['command gg','/gg','command ready','/ready'])assert.ok(api.t(commandKey).includes(example),lang+': '+example);
  for(const example of ['comma','period','question mark'])assert.ok(api.t(punctuationKey).includes(example),lang+': '+example);
 }
 const source=fs.readFileSync(path.resolve(__dirname,'../src/index.tsx'),'utf8');
 assert.ok(source.includes('setRpcError(t(result.error || "Binding cancelled.'));
 assert.ok(source.includes('onCancelButton={swallow}'));
});
