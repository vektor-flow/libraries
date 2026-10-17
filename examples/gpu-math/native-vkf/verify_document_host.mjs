import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,mkdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';
const registry=JSON.parse(readFileSync(new URL('./host/tests/registry.json',import.meta.url)));
const root=process.env.VKF_HOST_OUTPUT_DIR ?? mkdtempSync(join(tmpdir(),'vkf-document-host-'));
for(const suite of registry) test(suite.file,()=>{
 const out=join(root,suite.file);mkdirSync(out,{recursive:true});
 const child=spawnSync(process.execPath,[fileURLToPath(new URL('./host/tests/'+suite.file,import.meta.url)),'candidate'],{encoding:'utf8',timeout:30000,env:{...process.env,VKF_HOST_RESULT_DIR:pathToFileURL(out+'/').href}});
 assert.equal(child.error,undefined,String(child.error));
 assert.equal(child.status,0,child.stderr);
 const result=JSON.parse(child.stdout.trim());assert.equal(result.passed,true);
 assert.deepEqual(result.checks,suite.groups.map(g=>g.description));
 for(const g of suite.groups) console.log('PASS '+g.id+' '+g.description);
});
