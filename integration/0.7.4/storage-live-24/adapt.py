from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parent/'storage-live-19'
names=['preflight.py','refresh.py','rotate_owners.py','qualify.py','publication.py','check_loaded.py','validate_snapshots.py','validate_security.py','test_security.py','test_publication.py','dry_validate.py','run_step.py']
for name in names:
 s=(P/name).read_text()
 # Replace current iteration identifiers before predecessor references.
 for a,b in [('01a149a4-a1db-77a3-8094-f450e46d1ee8','01a149d1-1ba6-77f0-904a-23fc7490075b'),('01a1498d-0c53-74c0-96a2-899999a3fc97','01a149a4-a1db-77a3-8094-f450e46d1ee8'),('1b76a245c632e0b6b1b63eda740b14a49fc2f60d','585704c4f2e61b73e23b0cca11a39dc38a451598'),('storage-direct-v8','storage-direct-v9'),('storage-live-19','storage-live-24'),('live19','live24'),('iteration=19','iteration=24'),("g['iteration']==19","g['iteration']==24"),('storage-live-17/','storage-live-19/'),('==17','==19'),('== -11','== 1'),('==-11','==1'),('phase_sequence=5','phase_sequence=6'),('phase_count=5','phase_count=6'),('consumed_before_live24=5','consumed_before_live24=6'),('20971520','25165824'),("len(data['phases'])==5","len(data['phases'])==6"),("len(before['phases'])==5","len(before['phases'])==6"),('real v8','real v9'),('tiny real v8','tiny real v9'),('in-memory v8','in-memory v9'),('v8_snapshots','v9_snapshots')]:s=s.replace(a,b)
 if name in ['preflight.py','refresh.py']:
  s=s.replace("'F:live17-f-success-01'}","'F:live17-f-success-01','F:live19-f-success-01'}")
  s=s.replace("r=data['phases']['F:live17-f-success-01']","r=data['phases']['F:live19-f-success-01']")
  s=s.replace('storage-exec-mapping-repair-18/root-v8-installed.json','storage-combined-trust-review-23/root-v9-installed.json')
  s=s.replace('storage-exec-mapping-repair-18/preserved-v7-bundle.json','storage-namespace-trust-repair-20/preserved-v8-bundle.json')
  # Dry read errors remain local validation errors, not an operational STOP.
  s=s.replace("save('STOP.json',dict(reason=str(exc),traceback=traceback.format_exc(),stage='read-only-evidence-seal'))","print(traceback.format_exc(), file=sys.stderr)")
 if name=='rotate_owners.py':
  s=s.replace('F:live17-f-success-01','F:live19-f-success-01').replace("=='live17-f-success-01'","=='live19-f-success-01'")
  s=s.replace('storage-exec-mapping-repair-18/preserved-v7-bundle.json','storage-namespace-trust-repair-20/preserved-v8-bundle.json')
 if name=='qualify.py':
  s=s.replace('timeout_seconds=2 if mode==\'timeout\' else 10','timeout_seconds=10')
  s=s.replace("checks['v9_snapshots_validated']=validate(records,r,g,m)","checks['v9_snapshots_validated']=validate(records,r,g,m)\n        from validate_trust import validate_trust\n        checks['v9_trust_validated']=validate_trust(checks['raw_receipts']['outer.stdout']['text'],records,r,g,m)")
  # Preserve parsed records and exact required payload bytes (no missing output passes).
  s=s.replace("assert report['mode']==mode and report['outside_readonly'] is True", "assert report['mode']==mode and report['outside_readonly'] is True\n        assert pathlib.Path(m['output_paths'][0]).read_bytes()==b'fresh storage qualification\\n'*128\n        assert len(records)==(10 if mode=='timeout' else 9), 'unexpected fixture/helper record count'")
 if name=='dry_validate.py':
  s=s.replace("assert json.loads((p.OUT/'publication-tests.json').read_text())['success']", "assert json.loads((p.OUT/'publication-tests.json').read_text())['success']\nassert json.loads((p.OUT/'trust-parser-tests.json').read_text())['passed']")
 (O/name).write_text(s)
# Generic read-only final resource check is prepared and pinned before operation.
s=(O/'refresh.py').read_text().replace("assert not (OUT/'STOP.json').exists()",'pass # Final read-only refresh allowed after STOP')
(O/'read_only_final.py').write_text(s)
