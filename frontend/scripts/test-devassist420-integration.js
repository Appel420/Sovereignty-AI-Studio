const fs=require('fs');const path=require('path');const vm=require('vm');const assert=require('assert');
const source=fs.readFileSync(path.join(__dirname,'..','runtime','devassist420-integration.js'),'utf8');
function load(fetchImpl,ownerSession){const sandbox={console,isSecureContext:true,location:{protocol:'https:'},fetch:fetchImpl,addEventListener:()=>{},document:null,SGHV119_OWNER_SESSION:ownerSession};sandbox.window=sandbox;vm.runInNewContext(source,sandbox);return sandbox;}
function response(body,ok=true,status=200){return{ok,status,json:async()=>body};}
(async()=>{
let calls=[];const sandbox=load(async(url,options)=>{calls.push({url,options});if(url.endsWith('/status'))return response({status:'healthy'});if(url.endsWith('/session/open'))return response({session_id:'owner-session-1'});if(url.endsWith('/proposal'))return response({decision:'ACCESS_DENIED',reason:'policy'});return response({decision:'AUTHORIZED',result:'executed'});},'device-owner-authenticated-token');
const runtime=sandbox.SGHV119DevAssist.create({endpoint:'/api/devassist'});assert.strictEqual(runtime.state,'SIGNED_OUT');await runtime.status();await runtime.beginSession({source:'SGHv119'});assert.strictEqual(runtime.state,'SESSION_ACTIVE');
const denied=await runtime.propose({resource:'file:test',operation:'read',purpose:'test'});assert.strictEqual(denied.decision,'ACCESS_DENIED');await assert.rejects(()=>runtime.executeApproved({decision:'ACCESS_DENIED'}),/REQUIRES_AUTHORIZED_RECEIPT/);
await runtime.closeSession();assert.strictEqual(runtime.state,'CLOSED');assert.strictEqual(runtime.sessionId,null);assert.deepStrictEqual(Object.keys(runtime.transientState),[]);
const closeCall=calls.find(c=>c.url.endsWith('/session/close'));assert.ok(closeCall);assert.ok(closeCall.options.body.includes('"destroy_transient_state":true'));assert.ok(closeCall.options.body.includes('"revoke_capabilities":true'));
const unauth=load(async()=>response({session_id:'should-not-be-created'}));const unauthRuntime=unauth.SGHV119DevAssist.create();await assert.rejects(()=>unauthRuntime.beginSession(),/OWNER_AUTHENTICATION_REQUIRED/);
const insecure=load(async()=>response({status:'healthy'}),'owner-token');insecure.location.protocol='http:';insecure.isSecureContext=false;const insecureRuntime=insecure.SGHV119DevAssist.create();await assert.rejects(()=>insecureRuntime.status(),/TRANSPORT_NOT_SECURE/);
const executeSandbox=load(async(url)=>{if(url.endsWith('/session/open'))return response({session_id:'s'});return response({decision:'AUTHORIZED'});},'owner-token');const executeRuntime=executeSandbox.SGHV119DevAssist.create();await executeRuntime.beginSession();const result=await executeRuntime.executeApproved({decision:'AUTHORIZED',capability:'test'});assert.strictEqual(result.decision,'AUTHORIZED');
console.log('DevAssist420 SGHv119 integration boundary tests: PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
