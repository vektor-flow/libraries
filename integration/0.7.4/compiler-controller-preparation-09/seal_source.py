"""Host-only streaming seal; reads static source/config, never owner/state outcomes."""
import ast
from pathlib import Path
import adapter as a
S = Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')
v6 = S/'storage-direct-v6'
setup = a.HERE.parent/'storage-policy-setup-11'
installed = a.read(setup/'root-installed.json')
for p in installed['installed_files']: a.verify(p)
helpers = ['storage_admission.py','storage_paths.py','terminal_recovery.py','private_workload.py','effective_storage.py']
bundle = dict(controller=a.pin(v6/'storage_controller.py'), helpers=[a.pin(v6/n) for n in helpers], config=a.pin(v6/'runtime-config.json'))
config = a.read(v6/'runtime-config.json')
policy_pin = config['approved_policies'][1]
policy = a.load_pin(policy_pin)
assert policy['root']['path'] and policy['coordinator'] == a.COORDINATOR
pins = installed['installed_files']+a.read(setup/'binary-contract.json')+a.read(setup/'policy-inputs.json')
# Compare installed helper constants without importing operational modules.
constants = {}
for node in ast.parse((v6/'private_workload.py').read_text()).body:
    if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('BINARIES','POLICY_INPUTS'):
        constants[node.targets[0].id] = ast.literal_eval(node.value)
assert constants['BINARIES'] == a.read(setup/'binary-contract.json')
assert constants['POLICY_INPUTS'] == a.read(setup/'policy-inputs.json')
pins += [a.pin(a.PACKAGE/n) for n in ('authenticate.py','prepare.py','payload.py','authentication.json','SPEC.txt')]
pins += [a.pin(a.HERE/'adapter.py'),a.pin(setup/'root-installed.json')]
pins += [a.pin(a.HERE.parent/'compiler-native-binding-08'/n) for n in ('corrected-review.json','root-acceptance.json')]
pins += [policy_pin,policy['predecessor_controller'],policy['predecessor_ledger'],a.pin(S/'owned-processes.py')]
# Include every enrolled policy for the authority-root exclusion check.
pins += config['approved_policies']
for p in a.unique(pins): a.verify(p)
obj = dict(schema=1, source_commit='b1aaaecb3702d86341c4366c91e09de2d8dd8e19',
           v6_bundle=bundle, a_policy=policy_pin, owned_processes=a.pin(S/'owned-processes.py'),
           python=a.pin('/usr/bin/python3.14'),
           review=a.pin(a.HERE.parent/'compiler-native-binding-08/corrected-review.json'),
           state_path=str(S/'storage-direct-v4/direct-state-v4.json'),lock_path=str(S/'capacity.lock'),
           pins=a.unique(pins))
a.save(a.HERE/'source-contract.json',obj)
print('sealed static pins:',len(obj['pins']))
