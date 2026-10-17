"""Read-only preflight, NOT a VKF parser, compiler or PDF acceptance test.

Exit 2 means the intended calls cannot match the current single-line facade.
Exit 0 only permits a separately authorized native syntax/behavior check.
"""
import argparse
import json
import re
from pathlib import Path


def gaps(text):
    signatures = re.findall(r'^tex2pdf\(([^\n]*)\)(?:->[^:\n]+)?:\s*$', text, re.M)
    if len(signatures) != 1:
        return ['Expected one single-line tex2pdf signature; inspect manually']
    # Deliberately accept only the scalar/vector/named-record parameter grammar
    # used by this facade. Fail closed on nested defaults or unfamiliar syntax.
    parameters = {}
    for item in signatures[0].split(','):
        match = re.fullmatch(r'\s*(\w+)\s*:\s*([\w\[\]]+)\s*(?:=\s*(.*?))?\s*', item)
        if not match or match[1] in parameters:
            return ['Unsupported or duplicate parameter syntax; inspect manually']
        parameters[match[1]] = (match[2], match[3])
    errors = []
    for name, kind, default in [('source', 'str', None), ('dest', 'str', '""'),
                                ('selectable', 'bit', 'true'), ('editable', 'bit', 'false')]:
        if name not in parameters:
            errors.append('Missing direct parameter: ' + name)
        elif parameters[name] != (kind, default):
            errors.append('Wrong type/default: ' + name)
    if next(iter(parameters), None) != 'source':
        errors.append('First positional parameter must be source')
    required = [name for name, (_, default) in parameters.items()
                if name != 'source' and default is None]
    if required:
        errors.append('Source-only named call still requires: ' + ', '.join(required))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    path = args.repo / 'examples/gpu-math/native-vkf/latex.vkf'
    errors = gaps(path.read_text())
    print(json.dumps({'scope': 'signature preflight only', 'path': str(path.resolve()),
                      'gaps': errors, 'ready_for_native_check': not errors,
                      'native_executed': False, 'pdf_acceptance': 'unqualified'}, indent=2))
    return 2 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
