"""Bounded host/source review checks. No compiler, renderer or operational access."""
import hashlib,json,re,subprocess,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
NATIVE=REPO/'examples/gpu-math/native-vkf'
C=HERE/'candidate'
sha=lambda b:hashlib.sha256(b).hexdigest()

def verify_binding(binding):
    for row in binding['assets'].values():
        data=Path(row['path']).read_bytes()
        if len(data)!=row['bytes'] or sha(data)!=row['sha256']:raise ValueError('Resource identity mismatch')
    roles=binding['ordered_roles_json']
    if sha(roles.encode())!=binding['ordered_roles_sha256']:raise ValueError('Role order changed')
    identity=['vkf.latex.resources/1',*[binding['assets'][r]['sha256'] for r in ['fonts','operators','language']],binding['ordered_roles_sha256']]
    if binding['resource_revision']!='sha256:'+sha(json.dumps(identity,separators=(',',':')).encode()):raise ValueError('Resource revision mismatch')
    return True

def signature(source,name):
    return re.findall(r'^'+name+r'\((.*)\)(?:->[^:]+)?:$',source,re.M)

def check_transport(source,baseline):
    # Independent invariant: exactly one original-layout call and encode that
    # exact returned document. Return all of Result, not a reconstruction.
    expected='source,fonts,ordered_roles,language,files_json,job,entry,include_layout,a261_blocks,a261_scopes,a261_texts,a263_kinds,a267_notes,a267_scopes,a267_texts,a267_kinds'
    if source.count('document_materialize.layout(')!=1 or 'result:document_materialize.layout('+expected+')' not in source:raise ValueError('Layout invocation/input mismatch')
    if 'result.complete? .pdf:document_pdf_bulk.encode(result.document,fonts,operators)' not in source:raise ValueError('Encode document/completeness mismatch')
    if '@:(pdf:pdf,layout:result)' not in source:raise ValueError('Typed result lost')
    for typename in ['Metadata','Catalog','Language','Paint','Payload','Arena','PageDocument','Result']:
        a=re.search('^'+typename+r':.*$',source,re.M).group()
        b=re.search('^'+typename+r':.*$',baseline,re.M).group()
        if a!=b:raise ValueError('Typed schema mismatch '+typename)
    if signature(source,'render')!=signature(baseline,'render'):raise ValueError('Positional transport drift')
    return True

class ProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding=json.loads((HERE/'resource-binding.json').read_bytes())
        cls.materialize=(NATIVE/'document_materialize.vkf').read_text()
        cls.transport=(C/'latex_render_result.vkf').read_text()

    def test_all_input_pins_still_match(self):
        for row in json.loads((HERE/'input-pins.json').read_bytes()):
            with self.subTest(path=row['path']):self.assertEqual(sha(Path(row['path']).read_bytes()),row['sha256'])

    def test_exact_accepted_resources(self):
        self.assertTrue(verify_binding(self.binding))
        self.assertEqual(set(self.binding['assets']),{'fonts','operators','language'})
        self.assertEqual(sum(x['bytes'] for x in self.binding['assets'].values()),21292928)
        self.assertEqual(len(json.loads(self.binding['ordered_roles_json'])),24)

    def test_missing_wrong_resource_and_role_order_rejected(self):
        broken=json.loads(json.dumps(self.binding));broken['assets']['fonts']['path']=str(HERE/'missing-font-do-not-create')
        with self.assertRaises(FileNotFoundError):verify_binding(broken)
        broken=json.loads(json.dumps(self.binding));broken['assets']['operators']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'identity'):verify_binding(broken)
        broken=json.loads(json.dumps(self.binding));broken['ordered_roles_json']=json.dumps(list(reversed(json.loads(broken['ordered_roles_json']))))
        with self.assertRaisesRegex(ValueError,'Role order'):verify_binding(broken)

    def test_actual_font_roles_and_operator_ranges(self):
        # Read real accepted installed assets; no generated/test-font substitute.
        data=Path(self.binding['assets']['fonts']['path']).read_bytes()
        self.assertEqual(data[:32],b'VKF-FONT-CATALOG/1              ')
        capacity,count,payload_size=[int(data[p:p+12]) for p in (32,44,56)]
        payload=68+capacity*36
        self.assertEqual(payload_size,len(data)-payload)
        roles=set(json.loads(self.binding['ordered_roles_json']));found=set();paths=0;entries=0
        operator_size=self.binding['assets']['operators']['bytes']
        for i in range(capacity):
            base=68+i*36;start,ks,vs=[int(data[base+p:base+p+12]) for p in (0,12,24)]
            if not start:continue
            entries+=1
            self.assertGreaterEqual(start,payload);self.assertLessEqual(start+ks+vs,len(data))
            key=data[start:start+ks].decode('utf-8')
            if key.startswith('font/') and key[5:] in roles:
                self.assertIsInstance(json.loads(data[start+ks:start+ks+vs]),dict);found.add(key[5:])
            if key.startswith('path/'):
                item=json.loads(data[start+ks:start+ks+vs]);offset,length=item['offset'],item['length']
                self.assertGreaterEqual(offset,0);self.assertGreaterEqual(length,0);self.assertLessEqual(offset+length,operator_size);paths+=1
        self.assertEqual(entries,count);self.assertEqual(found,roles);self.assertGreater(paths,0)
        print(json.dumps({'real_catalog_records':entries,'real_vector_ranges':paths,'real_font_roles':len(found)}))

    def test_actual_language_header_and_extents(self):
        data=Path(self.binding['assets']['language']['path']).read_bytes()
        self.assertEqual(data[:32],b'VKF-HYPHENATION/1               ')
        nodes,edges,weights,exceptions,size=[int(data[p:p+8]) for p in (32,40,48,56,64)]
        self.assertGreater(nodes,0);self.assertGreater(edges,0)
        self.assertEqual(72+20*nodes+9*edges+weights+size,len(data))

    def test_loader_uses_existing_functions_and_exact_resource_bytes(self):
        source=(C/'latex_default_resources.vkf').read_text()
        literals=[json.loads(x) for x in re.findall(r'io.read_text\(("(?:[^"\\]|\\.)*")\)',source)]
        self.assertEqual(literals,[self.binding['assets'][r]['path'] for r in ['fonts','operators','language']])
        raw=re.search(r'text_parser_kernel.roles\(("(?:[^"\\]|\\.)*")\)',source).group(1)
        self.assertEqual(json.loads(raw),self.binding['ordered_roles_json'])
        self.assertIn(self.binding['resource_revision'],source)
        self.assertIn('(fonts.size=11866638)?!',source)
        self.assertIn('(tex_text.byte_length(operators)=9197368)?!',source)
        self.assertIn('(language.size=228922)?!',source)
        for module in ['font_catalog','hyphenation','text_parser_kernel']:
            self.assertTrue((NATIVE/(module+'.vkf')).exists())
        self.assertNotIn('test_font',source);self.assertNotIn('files.json',source)

    def test_legacy_prefixes_and_optional_owner_columns_unchanged(self):
        for name in ['latex.vkf','latex_library.vkf']:
            baseline=(NATIVE/name).read_text();candidate=(C/name).read_text()
            self.assertTrue(candidate.startswith(baseline))
            self.assertEqual(signature(candidate,'tex2pdf')[0],signature(baseline,'tex2pdf')[0])
        self.assertEqual(len(signature((C/'latex.vkf').read_text(),'tex2pdf')),2)
        public=signature((C/'latex.vkf').read_text(),'tex2pdf')[1]
        self.assertTrue(public.startswith('source:str,dest:str="",selectable:bit=true,editable:bit=false,'))
        for name in ['fonts:','operators:','ordered_roles:','language:']:self.assertNotIn(name,public)

    def test_unsupported_modes_fail_before_loading_or_rendering(self):
        s=(C/'latex_library.vkf').read_text().split('\ntex2pdf_named(',1)[1]
        self.assertLess(s.index('(dest="")?!'),s.index('resources:latex_default_resources.load()'))
        self.assertLess(s.index('(~(selectable \\/ editable))?!'),s.index('resources:latex_default_resources.load()'))
        self.assertNotIn('io.write',s);self.assertNotIn('encode_selected',s)
        self.assertEqual(s.count('@:tex2pdf('),1)

    def test_same_layout_and_complete_typed_schema(self):
        self.assertTrue(check_transport(self.transport,self.materialize))
        for name in ['a260_scopes','a260_texts','a260_operations','a260_starts','a260_stops','a260_parts']:
            self.assertIn(name,self.transport)

    def test_transport_mutations_rejected(self):
        mutants=[self.transport.replace('encode(result.document,','encode(other.document,'),
                 self.transport.replace('result.complete? .pdf:','true? .pdf:'),
                 self.transport.replace('@:(pdf:pdf,layout:result)','@:(pdf:pdf)'),
                 self.transport.replace(',a267_kinds)',')'),
                 self.transport.replace('a260_parts:[int]','a260_parts:[num]')]
        for mutant in mutants:
            with self.assertRaises(ValueError):check_transport(mutant,self.materialize)

    def test_patches_apply_read_only_and_only_owned_source_scope(self):
        for name,expected in [('source-api.patch',{'latex.vkf','latex_library.vkf','latex_default_resources.vkf'}),('typed-result.patch',{'latex_render_result.vkf'})]:
            p=HERE/name
            touched={Path(x).name for x in re.findall(r'^\+\+\+ b/(.*)$',p.read_text(),re.M)}
            self.assertEqual(touched,expected)
            result=subprocess.run(['git','apply','--check',str(p)],cwd=REPO,capture_output=True,text=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_transport_authentication_is_explicit_dependency(self):
        c=json.loads((HERE/'TRANSPORT-CONTRACT.json').read_bytes())
        self.assertFalse(c['native_acceptance']);self.assertFalse(c['public_api_complete'])
        self.assertEqual(len(c['native_argument_order']),17)
        self.assertEqual(c['legacy_default_color'],[0,0,0,1])
        self.assertEqual(c['selection_plan_owner'],'pdf-selection-implementation-22; schema intentionally not duplicated here')
        bridge=(NATIVE/'host/latex_source_binding_bridge.mjs').read_text()
        for guard in ['issued.has(preparation)','issued.get(preparation) === edits.current','check(detached?.document','bindOperationDocument(detached, preparation.owner']:
            self.assertIn(guard,bridge)
        operation=(NATIVE/'host/latex_operation_binding.mjs').read_text()
        self.assertIn('Unbound/generated operation',operation)
        self.assertIn('Unconsumed owner leaf mapping',operation)

    def test_future_cases_are_unexecuted_and_use_real_api(self):
        cases=json.loads((HERE/'native-fixtures/cases.json').read_bytes())
        self.assertEqual(len(cases),7);self.assertTrue(all(c['executed'] is False for c in cases))
        source=(HERE/'native-fixtures/direct-legacy-parity.vkf').read_text()
        self.assertIn('latex.tex2pdf(source,editable:false,files_json:files,selectable:false)',source)
        self.assertIn('typed.pdf=legacy.pdf',source)
        for c in cases:self.assertTrue((HERE/'native-fixtures'/c['file']).exists())

if __name__=='__main__':unittest.main(verbosity=2)
