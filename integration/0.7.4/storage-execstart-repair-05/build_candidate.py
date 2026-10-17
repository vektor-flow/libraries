"""Build review artifacts only, rooted beside this script."""
from pathlib import Path
import difflib, shutil
O=Path(__file__).resolve().parent
D=O/'candidate'/'storage-direct-v3'
D.mkdir(parents=True,exist_ok=True)
s=(O/'original-storage_controller.py').read_text()
s=s.replace('Inactive v2 successor.', 'Inactive v3 code successor; preserved v2 ledger/grant protocol.')
s=s.replace("HERE = Path(__file__).resolve().parent", "HERE = Path(__file__).resolve().parent\nSTATE_HOME = HERE.parent/'storage-direct-v2'  # One preserved ledger; never initialize a new one.")
s=s.replace("Ledger(HERE/'direct-state-v2.json', HERE.parent/'capacity.lock')", "Ledger(STATE_HOME/'direct-state-v2.json', STATE_HOME.parent/'capacity.lock')")
# Insert strict parsers without weakening the caller's exact argv equality.
parser='''def typed_json(raw, signature):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate D-Bus JSON key')
            result[key] = value
        return result
    try:
        obj = json.loads(raw, object_pairs_hook=pairs)
    except (ValueError, TypeError) as error:
        raise RuntimeError('invalid D-Bus JSON') from error
    require(type(obj) is dict and set(obj) == {'type', 'data'}
            and obj['type'] == signature and type(obj['data']) is list,
            'D-Bus signature/envelope')
    return obj['data']


def parse_get_unit(raw):
    data = typed_json(raw, 'o')
    require(len(data) == 1 and type(data[0]) is str
            and re.fullmatch(r'/org/freedesktop/systemd1/unit/[A-Za-z0-9_]+', data[0]),
            'GetUnit object path')
    return data[0]


def parse_exec_start(raw):
    # busctl get-property unwraps the property variant. data IS the array of
    # structs, unlike an extra message-body wrapper. Recorded systemd259 fixture.
    data = typed_json(raw, 'a(sasbttttuii)')
    require(len(data) == 1 and type(data[0]) is list and len(data[0]) == 10,
            'single ten-field ExecStart required')
    command = data[0]
    path, argv, ignore_failure = command[:3]
    require(type(path) is str and path.startswith('/') and '\\0' not in path
            and type(argv) is list and len(argv) > 0
            and all(type(x) is str and '\\0' not in x for x in argv)
            and path == argv[0] and ignore_failure is False, 'ExecStart flags/path/argv')
    for index, bits, signed in ((3,64,False),(4,64,False),(5,64,False),(6,64,False),
                                (7,32,False),(8,32,True),(9,32,True)):
        n = command[index]
        low, high = (-(2**(bits-1)), 2**(bits-1)) if signed else (0, 2**bits)
        require(type(n) is int and low <= n < high, 'ExecStart integer field')
    return command


'''
s=s.replace('class Linux:',parser+'class Linux:')
a=s.index('        obj = json.loads(self.output(',s.index('    def argv(')); b=s.index('\n    def units(',a)
s=s[:a]+'''        obj = parse_get_unit(self.output(['busctl', '--user', '--json=short', 'call',
            'org.freedesktop.systemd1', '/org/freedesktop/systemd1',
            'org.freedesktop.systemd1.Manager', 'GetUnit', 's', unit]))
        value = self.output(['busctl', '--user', '--json=short', 'get-property',
            'org.freedesktop.systemd1', obj, 'org.freedesktop.systemd1.Service', 'ExecStart'])
        return parse_exec_start(value)[1]
''' + s[b:]
# Explicit trusted bundle allowlist, not loose acceptance of any hash supplied by old grant.
a=s.index('    def authenticate_record(')
s=s[:a]+'''    def authenticate_record_sources(self, r):
        g = pinned_json(r['grant'])
        c = r['custody']
        bundle = dict(controller=g['controller'], helpers=g['helpers'], config=c['config'])
        own = dict(controller=pin(HERE/'storage_controller.py'),
                   helpers=[pin(HERE/n) for n in HELPERS], config=self.config_pin)
        require(bundle == own or bundle in self.config.get('preserved_record_authorities', []),
                'unapproved historical controller/helper/config bundle')
        for p in [bundle['controller'], *bundle['helpers'], bundle['config']]:
            pinned(p)

''' +s[a:]
s=s.replace("        g, m = pinned_json(r['grant']), pinned_json(r['manifest'])\n        c = r['custody']", "        self.authenticate_record_sources(r)\n        g, m = pinned_json(r['grant']), pinned_json(r['manifest'])\n        c = r['custody']")
s=s.replace("                and g['controller'] == pin(HERE/'storage_controller.py')\n                and g['helpers'] == [pin(HERE/n) for n in HELPERS]\n",'')
# current() still requires fresh grants to pin the executing NEW controller.
a=s.index('    def outer(self):')
s=s[:a]+'''    def seal_incomplete(self, r, *, outer_exit=None, transport_error=None):
        failure = dict(schema='storage-controller-failure-v1', phase=self.key,
            result='controller-failed-before-authenticated-completion', passed=False,
            failure_kind=('service-attach-missing' if 'service' not in r else
                          'inner-completion-missing' if 'inner_result' not in r else 'unexpected-stage'),
            workload_result=None, stage=r['stage'], grant=self.gp, manifest=self.mp,
            custody=r['custody'], missing=[k for k in ('service', 'inner_result') if k not in r],
            outer_exit=outer_exit, transport_error=transport_error,
            disk_charge_retained=r['phase_bytes'], ram_intent_retained=r['ram_bytes'],
            recovery_required=True)
        failure['transport_logs'] = [pin(p) for p in
            [Path(self.m['receipts'])/'outer.stdout', Path(self.m['receipts'])/'outer.stderr']
            if p.is_file()]
        # Observations aid diagnosis; they are never a join or release authority.
        try:
            failure['observed_service'] = self.os.show(r['custody']['unit'])
        except Exception as error:
            failure['observation_error'] = type(error).__name__+': '+str(error)
        try:
            receipt = self.write_receipt('controller-failure.json', failure)
        except Exception as error:
            raise RuntimeError('controller failed; failure receipt NOT sealed; '
                               'disk and RAM retained; no authenticated completion') from error
        print(json.dumps(dict(result=failure['result'], passed=False, failure_receipt=receipt)),
              file=sys.stderr)
        return 125

''' +s[a:]
a=s.index("        with open(Path(self.m['receipts'])/'outer.stdout'"); b=s.index('        receipt = dict(grant=',a)
s=s[:a]+'''        try:
            with open(Path(self.m['receipts'])/'outer.stdout', 'xb') as out, open(Path(self.m['receipts'])/'outer.stderr', 'xb') as err:
                result = subprocess.run(run_command(r, self.g), timeout=self.g['timeout_seconds']+60,
                                        stdout=out, stderr=err)
        except (OSError, subprocess.TimeoutExpired) as error:
            r = self.ledger.snapshot()['phases'][key]
            return self.seal_incomplete(r, transport_error=type(error).__name__+': '+str(error))
        r = self.ledger.snapshot()['phases'][key]
        if r['stage'] != 'inner_finished' or 'service' not in r or 'inner_result' not in r:
            return self.seal_incomplete(r, outer_exit=result.returncode)
''' + s[b:]
(D/'storage_controller.py').write_text(s)
for n in ('storage_admission.py','storage_paths.py'):
 shutil.copyfile(O/('original-'+n),D/n)
changes=''.join(difflib.unified_diff((O/'original-storage_controller.py').read_text().splitlines(True),s.splitlines(True),fromfile='installed-v2/storage_controller.py',tofile='candidate/storage-direct-v3/storage_controller.py'))
(O/'controller-review.diff').write_text(changes)
patch=''
for p in sorted(D.iterdir()):
 patch+=''.join(difflib.unified_diff([],p.read_text().splitlines(True),fromfile='/dev/null',tofile='b/storage-direct-v3/'+p.name))
(O/'candidate-new-files.patch').write_text(patch)
