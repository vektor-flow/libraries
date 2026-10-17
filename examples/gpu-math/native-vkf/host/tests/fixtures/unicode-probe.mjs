// Test-only access to the exact private production implementation, read at runtime.
// No copied candidate algorithm and no public production export.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../../latex_operation_binding.mjs',import.meta.url),'utf8');
const start=source.indexOf('function createByteToUtf16Index(){');
const end=source.indexOf('function bind(',start);
assert.ok(start>=0&&end>start,'Production index function boundaries');
const check=source.split('\n').find(line=>line.startsWith('const check='));
const num=source.split('\n').find(line=>line.startsWith('const num='));
assert.ok(check&&num,'Production validation dependencies');
export const createByteToUtf16Index=Function(check+'\n'+num+'\n'+source.slice(start,end)+'\nreturn createByteToUtf16Index;')();
