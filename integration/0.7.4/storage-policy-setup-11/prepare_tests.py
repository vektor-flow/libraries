"""Prepare explicitly mocked source tests in this output only."""
from pathlib import Path
import shutil
H=Path(__file__).resolve().parent;P=H.parent/'storage-propagation-repair-10'
for n in ['preserve-v5-record-authority.json']:
 shutil.copyfile(P/n,H/n)
s=(P/'test_successor.py').read_text()
# New OS policy gates are mocked in inherited tests, separately adversarially
# tested in test_policy.py. No inherited success/failure/ledger assertions removed.
s=s.replace('class Wrapper(unittest.TestCase):','class Wrapper(unittest.TestCase):')
s=s.replace('        self.events=[]\n    def run_gate', "        self.events=[]\n        policy = patch.object(pw, 'policy_gate', return_value={'mock':True})\n        policy.start(); self.addCleanup(policy.stop)\n    def run_gate")
s=s.replace("with patch.object(sc.importlib.util,'spec_from_file_location',return_value=spec),", "with patch.object(pw,'policy_gate',return_value={'mock':True}),patch.object(sc.importlib.util,'spec_from_file_location',return_value=spec),")
s=s.replace("{'sandbox','Controller.current','Controller.inner'}", "{'sandbox','Controller.current','Controller.inner'}")
s=s.replace("        pw.verify_dependencies();self.assertEqual(pw.BINARIES,json.loads((HERE/'binary-contract.json').read_text()))", "        # Deployment is intentionally absent; validate unchanged installed binaries\n        # and the pinned source bytes of the proposed dedicated unshare copy.\n        for p in pw.BINARIES:\n            path=Path('/usr/bin/unshare') if p['path']==pw.UNSHARE else Path(p['path'])\n            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),p['sha256'])\n        self.assertEqual(pw.BINARIES,json.loads((HERE/'binary-contract.json').read_text()))")
s=s.replace("HERE/'sources/", "HERE.parent/'storage-propagation-repair-10/sources/")
(H/'test_successor.py').write_text(s)
# Parent/child bounded harness inherited; own directory and additional suite.
s=(P/'run_tests.py').read_text().replace('    import test_successor','    import test_successor\n    import test_policy')
s=s.replace('unittest.defaultTestLoader.loadTestsFromModule(inherited)])','unittest.defaultTestLoader.loadTestsFromModule(inherited),\n                             unittest.defaultTestLoader.loadTestsFromModule(test_policy)])')
s=s.replace('def child():\n','def child():\n    resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024,512*1024*1024))\n    resource.setrlimit(resource.RLIMIT_CPU, (45,45))\n')
(H/'run_tests.py').write_text(s)
