"""Read-only final pin/lexer provenance checks; writes only own report."""
import hashlib, json, resource, time
from pathlib import Path
from investigate import H, N, read, verify, pin, save, pins

def main():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CPU,(50,50))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    start=time.monotonic()
    original=read(H/'input-pins.json')
    for ref in original:verify(ref)
    source=read(H/'source-proof.json')
    profile_ref=read(H.parent/'metadata-control-preparation-27/packet-verification.json')['driver']['profile']
    verify(profile_ref);profile=read(profile_ref['path'])
    lexer=next(x for x in profile['objects'] if x['index']==232)
    assert lexer['object'] in read(N/'results.json')[2]['actual_dependencies']
    verify(lexer['object']);verify(lexer['actual_MD'])
    for d in lexer['dependencies']:verify(dict(path=d['effective'],sha256=d['sha256']))
    lexsource=Path(lexer['dependencies'][0]['effective'])
    lines=lexsource.read_text().splitlines()
    assert '    if (peek_literal(cursor, "::")) {' in lines
    assert '        emit_token(tokens, "EMIT", "", loc);' in lines
    verify(source['native17'])
    save('final-verification.json',dict(passed=True,seconds=time.monotonic()-start,
        original_input_pins_reverified=len(original),native17_unchanged=source['native17'],
        lexer_provenance=dict(object=lexer['object'],MD=lexer['actual_MD'],source=pin(lexsource),
                              actual_link_match=True,first_line=547,last_line=551,text='\n'.join(lines[546:551])),
        exact_source_pins=list(pins.values()),native_execution=False,operational_mutation=False,
        children=[],overlap=0,memory=[l for l in Path('/proc/self/status').read_text().splitlines()
                                    if l.startswith(('VmHWM:','VmPeak:'))]))
    print(json.dumps(dict(passed=True,seconds=time.monotonic()-start,
                         max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)))
if __name__=='__main__':main()
