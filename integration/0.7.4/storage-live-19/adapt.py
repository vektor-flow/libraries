from pathlib import Path
O=Path(__file__).resolve().parent; S=O.parent/'storage-live-17'
old='01a1498d-0c53-74c0-96a2-899999a3fc97'; new='01a149a4-a1db-77a3-8094-f450e46d1ee8'
files=['preflight.py','refresh.py','publication.py','test_publication.py','qualify.py','check_loaded.py','validate_security.py','validate_snapshots.py','run_step.py','dry_validate.py']
for name in files:
 s=(S/name).read_text().replace(old,new).replace('01a14978-0c64-7903-aea1-f81eb80b1cf4',old).replace('ec72b6b21d813994a6e02c77164b8c3baf074ba0','1b76a245c632e0b6b1b63eda740b14a49fc2f60d')
 s=s.replace('storage-direct-v7','storage-direct-v8').replace('storage-live-17','storage-live-19').replace('live17-','live19-').replace('iteration=17','iteration=19').replace("['iteration']==17","['iteration']==19").replace('before_live17=4','before_live19=5').replace('bytes_before_live17=16777216','bytes_before_live19=20971520').replace('vkf-storage-pre-v1','vkf-storage-pre-v2')
 if name in ['preflight.py','refresh.py']:
  s=s.replace("'F:live14-f-success-01'}","'F:live14-f-success-01','F:live17-f-success-01'}").replace('==16777216','==20971520').replace('16777216<=','20971520<=')
  s=s.replace("(OUT.parent/'storage-terminal-recovery-16/root-inspect.json').read_text())['state']","(OUT.parent/'storage-live-17/final-state.json').read_text())")
  s=s.replace("r=data['phases']['F:live09-f-success-01']","r=data['phases']['F:live17-f-success-01']").replace("r['inner_result']['exit']==1","r['inner_result']['exit']==-11")
  s=s.replace("storage-terminal-recovery-16/root-v7-installed.json","storage-exec-mapping-repair-18/root-v8-installed.json")
  s=s.replace("    artifact_pins=json.loads", "    assert config['preserved_record_authorities'][-1]==json.loads((OUT.parent/'storage-exec-mapping-repair-18/preserved-v7-bundle.json').read_text())\n    assert len(data['recovery_events'])==2\n    artifact_pins=json.loads")
 if name=='qualify.py':
  s=s.replace('tiny real v7 storage','tiny real v8 storage').replace("len(data['phases'])==4","len(data['phases'])==5").replace("v7_snapshots_validated","v8_snapshots_validated")
 if name=='publication.py':
  s=s.replace("and os.fstat(f.fileno()).st_uid==os.getuid()","and os.fstat(f.fileno()).st_uid==os.getuid() and os.fstat(f.fileno()).st_nlink==1")
 if name=='check_loaded.py':
  s=s.replace('len(records)==len(byname)==5','len(records)==len(byname)==7')
  s=s.replace("    assert all(x['mode']=='enforce' for x in records)","""    v2=json.loads((OUT.parent/'storage-exec-mapping-repair-18/compiled-profile-contract.json').read_text())
    combined2=bytearray(v2['combined_bytes'])
    for ref in v2['profiles']:
        raw=bytes.fromhex(byname[ref['name']]['raw'])
        assert hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref['bytes']
        combined2[ref['offset']:ref['offset']+len(raw)]=raw
    assert hashlib.sha256(combined2).hexdigest()==v2['combined_sha256']
    assert set(byname)=={'bwrap','unpriv_bwrap','unprivileged_userns','vkf-storage-pre-v1','vkf-storage-private-v1','vkf-storage-pre-v2','vkf-storage-private-v2'}
    assert all(x['mode']=='enforce' for x in records)""")
 if name=='dry_validate.py':
  s=s.replace('in-memory v7','in-memory v8').replace("(p.OUT.parent/'storage-terminal-recovery-16/root-inspect.json').read_text())['state']","(p.OUT.parent/'storage-live-17/final-state.json').read_text())").replace("storage-live-14/final-owner-state.json","storage-live-17/final-owner-state.json")
  s=s.replace('projection.rotate_owner(fp,verify_join=rot.forbidden_join)','projection.rotate_owner(fp,verify_join=rot.verify_normal_join)').replace('phase_sequence=4','phase_sequence=5').replace('projection.precommit_checks==1','projection.precommit_checks==0')
  s=s.replace('real_independent_join_calls=0','real_independent_join_calls=rot.join_calls').replace('real_fresh_terminal_checks=True','real_fresh_terminal_checks=True').replace('real_precommit_check=True','real_precommit_check=False,normal_F_succession=True')
  s=s.replace('exact real v7 state/owner/authority/terminal proof; recovered-F API and precommit projection','exact real v8 state/owner/authority/normal join; joined-F API projection')
 (O/name).write_text(s)
