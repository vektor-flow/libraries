"""Offline artifact checks only. Never establishes native provenance or timings.

Original: exact historical PDF bytes and strict 40-page/430-block report.
Edited-full: structure + changed PDF only, explicitly not edit acceptance.
Updated: exact PDF equality against separately root-qualified fresh edited-full
output. Root must bind both actual runs to the same edited source/resources.
New selectable PDFs require separate geometry/ownership/reader acceptance; they
must not bypass a legacy byte mismatch by switching this checker's case.
"""
import argparse
import json
from pathlib import Path
from pypdf import PdfReader
from prepare import HERE, check, pin, sha


def report_check(report, pdf_size):
    if report.get('complete') is not True:
        raise ValueError('Incomplete renderer report')
    for name, expected in [('pageCount', 40), ('blockCount', 430), ('pdfBytes', pdf_size)]:
        if type(report.get(name)) is not int or report[name] != expected:
            raise ValueError('Wrong report ' + name)
    for name in ('diagnostics', 'unresolved'):
        if report.get(name) != []:
            raise ValueError('Nonempty/missing ' + name)


def inspect(pdf, report):
    report_check(json.loads(Path(report).read_text()), Path(pdf).stat().st_size)
    reader = PdfReader(str(pdf), strict=True)
    if reader.is_encrypted or len(reader.pages) != 40:
        raise ValueError('PDF parser page/encryption mismatch')
    boxes = [[str(x) for x in page.mediabox] for page in reader.pages]
    return {'pdf': pin(pdf), 'report': pin(report), 'parser_pages': len(reader.pages), 'media_boxes': boxes}


def verify(pdf, report, case, reference_pdf=None, reference_report=None):
    manifest = json.loads((HERE / 'fixtures.json').read_text())
    check(manifest['binding'])
    check(manifest['original'])
    check(manifest['edited'])
    check(manifest['legacy_pdf'])
    check(manifest['legacy_report'])
    baseline = inspect(manifest['legacy_pdf']['path'], manifest['legacy_report']['path'])
    actual = inspect(pdf, report)
    if actual['media_boxes'] != baseline['media_boxes']:
        raise ValueError('Page geometry mismatch')
    if case == 'original':
        if actual['pdf']['sha256'] != manifest['legacy_pdf']['sha256']:
            raise ValueError('Legacy PDF byte mismatch; do not normalize/waive')
        level = 'legacy artifact parity only'
    elif case in ('edited-full', 'updated'):
        if actual['pdf']['sha256'] == manifest['legacy_pdf']['sha256']:
            raise ValueError('Small edit did not change PDF')
        level = 'changed full-document artifact structure only; correctness oracle pending'
        if case == 'updated':
            if not reference_pdf or not reference_report or Path(reference_pdf).resolve() == Path(pdf).resolve():
                raise ValueError('Separate fresh edited-full reference required')
            reference = inspect(reference_pdf, reference_report)
            if actual['pdf']['sha256'] != reference['pdf']['sha256']:
                raise ValueError('Update versus fresh-full PDF mismatch')
            actual['fresh_reference'] = reference
            level = 'update artifact parity only; independent run/source custody required'
    else:
        raise ValueError('Unknown case')
    return {'artifact_checks_passed': True, 'scope': level, 'case': case, **actual,
            'native_provenance_verified': False, 'public_api_qualified': False,
            'selection_qualified': False, 'editing_qualified': False, 'performance_qualified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['original', 'edited-full', 'updated'], required=True)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--reference-pdf', type=Path)
    parser.add_argument('--reference-report', type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.pdf, args.report, args.case, args.reference_pdf, args.reference_report)
    except Exception as error:
        print(json.dumps({'artifact_checks_passed': False, 'error': str(error),
                          'native_provenance_verified': False}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
