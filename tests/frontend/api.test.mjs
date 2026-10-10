import {test} from 'node:test';
import assert from 'node:assert/strict';
import {ApiClient,ApiError} from '../../mcias/web_workspace/api.js';
import {safeId,preferences,L} from '../../mcias/web_workspace/ui.js';

test('authorization remains memory-only and never enters URLs',async()=>{
 const api=new ApiClient();let request;
 globalThis.fetch=async(path,options)=>{request={path,options};return new Response('{"id":"authorized"}',{status:200,headers:{'Content-Type':'application/json'}});};
 api.setToken('synthetic_session_only');await api.request('/api/v1/workspace/context');
 assert.equal(request.options.headers.Authorization,'Bearer synthetic_session_only');assert.equal(request.options.credentials,'omit');assert.equal(request.options.cache,'no-store');assert.equal(request.options.redirect,'error');assert(!request.path.includes('synthetic_session_only'));
 api.clear();await api.request('/health/live');assert.equal(request.options.headers.Authorization,undefined);
});
test('204 logout is handled without parsing nonexistent JSON',async()=>{globalThis.fetch=async()=>new Response(null,{status:204});assert.equal(await new ApiClient().request('/api/v1/auth/logout',{method:'POST'}),null);});
test('expired authentication erases credentials and triggers reset',async()=>{const api=new ApiClient();let reset=false;api.setToken('synthetic');api.onExpiry=()=>{reset=true;};globalThis.fetch=async()=>new Response(null,{status:401});await assert.rejects(api.request('/api/v1/workspace/context'),e=>e instanceof ApiError&&e.status===401);assert(reset);let options;globalThis.fetch=async(_path,opts)=>{options=opts;return new Response('{}');};await api.request('/health/live');assert(!options.headers.Authorization);});
test('late protected response cannot survive logout',async()=>{const api=new ApiClient();let resolve;globalThis.fetch=()=>new Promise(r=>{resolve=r;});const pending=api.request('/api/v1/workspace/context');api.clear();resolve(new Response('{"private":"should not render"}'));await assert.rejects(pending,e=>e.name==='AbortError');});
test('network errors are sanitized and arbitrary URLs rejected',async()=>{const api=new ApiClient();globalThis.fetch=async()=>{throw Error('sensitive transport metadata');};await assert.rejects(api.request('/health/live'),e=>e.status===503&&!e.message.includes('sensitive'));await assert.rejects(api.request('https://external.invalid/patient-data'),/Same-origin/);});
test('synthetic preview blocks every consequential request',async()=>{const api=new ApiClient();api.demo({});let calls=0;globalThis.fetch=async()=>{calls++;return new Response('{}');};await assert.rejects(api.request('/api/v1/rules/id/activate',{method:'POST'}));assert.equal(calls,0);});
test('ID validation prevents path/query/script injection',()=>{assert.equal(safeId('test-id_1'),'test-id_1');for(const value of ['../../secrets','abc?token=1','<script>','abc/other',''])assert.throws(()=>safeId(value));});
test('UI language switches between Arabic and English',()=>{preferences.lang='ar';assert.equal(L('أدلة','Evidence'),'أدلة');preferences.lang='en';assert.equal(L('أدلة','Evidence'),'Evidence');preferences.lang='ar';});
test('response-body race cannot render protected data after logout',async()=>{const api=new ApiClient();let resolveBody;globalThis.fetch=async()=>({status:200,ok:true,json:()=>new Promise(resolve=>{resolveBody=resolve;})});const pending=api.request('/api/v1/workspace/context');await new Promise(setImmediate);api.clear();resolveBody({private:'do not render'});await assert.rejects(pending,e=>e.name==='AbortError');});
test('malformed JSON cannot expose its protected content in error text',async()=>{const api=new ApiClient();globalThis.fetch=async()=>new Response('PRIVATE PATIENT CONTENT');await assert.rejects(api.request('/api/v1/workspace/context'),e=>e.status===502&&!e.message.includes('PRIVATE'));});
