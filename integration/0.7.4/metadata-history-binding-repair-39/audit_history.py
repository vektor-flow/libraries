import argparse, hashlib, json, os, stat, subprocess, sys, time
from pathlib import Path
H=Path(__file__).resolve().parent
REPO=H.parents[2]
S=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')
sys.path.insert(0,str(S/'storage-direct-v9'))
from storage_paths import pinned,pinned_json,Rejected
from storage_controller import Controller
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 start=time.monotonic()
 statepath=S/'storage-direct-v4/direct-state-v4.json'
 before=statepath.read_bytes();state=json.loads(before)
 historical=json.loads((H.parent/'metadata-native-29/final-state.json').read_text())
 assert state==historical
 key,row=max(((k,r) for k,r in state['phases'].items() if r['worker']=='A'),key=lambda kv:kv[1]['sequence'])
 assert key=='A:metadata-native29-01' and row['sequence']==15 and row['stage']=='joined'
 assert row['owner']=='01a14a3a-d0d8-7a10-a188-717e31a22e31'
 assert row['join']['sha256']=='4a1ed5938463632747f40aba82b60beca7af7de4d676ed7e96ab9b01ea55f002'
 assert not any('native36' in k for k in state['phases'])
 manifest=pinned_json(row['manifest']);rows=[];fail=[]
 for ref in manifest['inputs']:
  p=Path(ref['path']);st=p.lstat();item=dict(pin=ref,mode=oct(stat.S_IMODE(st.st_mode)),uid=st.st_uid,nlink=st.st_nlink,owner_writable=bool(st.st_mode&stat.S_IWUSR),parent_owner_writable=bool(p.parent.stat().st_mode&stat.S_IWUSR),actual_sha256=sha(p))
  try: pinned(ref);item['verified']=True
  except Exception as e:item.update(verified=False,error=str(e));fail.append(item)
  rows.append(item)
 assert len(fail)==1
 expected=REPO/'integration/0.7.4/compiler-build-preparation-03/prepare.py'
 assert fail[0]['pin']==dict(path=str(expected),sha256='fd49773772924b2ccf59b4a9386dc5e22a1062cc8176391c6a0ed5058713ffda')
 assert fail[0]['actual_sha256']=='400a56b07d9cb67c7d4d9331a787d13af43fd60dfba56a09481e88b9f66de169'
 seal=json.loads((H.parent/'metadata-repaired-binding-32/source-contract.json').read_text())
 ctrl=Controller(argparse.Namespace(config_sha256=seal['v6_bundle']['config']['sha256'],grant=Path(row['grant']['path']),grant_sha256=row['grant']['sha256'],manifest=Path(row['manifest']['path']),manifest_sha256=row['manifest']['sha256']))
 try: ctrl.verify_join(row,pinned_json(row['join']))
 except Rejected as e: assert str(e)=='source pin mismatch';join_error=str(e)
 else:raise AssertionError('expected installed predecessor rejection')
 old=subprocess.check_output(['/usr/bin/git','-C',str(REPO),'show','9dbabcaea9fce28129469e31a139a8548a14ab22:integration/0.7.4/compiler-build-preparation-03/prepare.py'])
 assert hashlib.sha256(old).hexdigest()==fail[0]['pin']['sha256']
 (H/'historical-prepare.py').write_bytes(old)
 assert before==statepath.read_bytes()
 result=dict(passed=True,manifest=row['manifest'],manifest_inputs=len(rows),mismatches=fail,owner_writable_inputs=sum(x['owner_writable'] for x in rows),replaceable_parent_inputs=sum(x['parent_owner_writable'] for x in rows),inputs=rows,actual_installed_verify_join_error=join_error,full_join_verified=False,state_unchanged=True,latest=dict(key=key,sequence=row['sequence'],owner=row['owner'],join=row['join']),native36_row_exists=False,seconds=time.monotonic()-start)
 (H/'history-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('inputs','mismatches')}))
main()
