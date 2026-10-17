import hashlib,json,os
import private_workload

def validate(records,row,g,m):
    snaps=[x for x in records if 'private_workload_snapshot' in x]
    assert len(snaps)==2 and [x['private_workload_snapshot'] for x in snaps]==['pre','post']
    argv=row['inner_result']['sandbox_argv'];origin=json.loads(argv[argv.index('pre')+1])
    assert origin['cgroup']==row['custody']['cgroup'] and origin['uid']==os.getuid()!=0 and origin['gid']==os.getgid()
    for s in snaps:
        stage=s['private_workload_snapshot'];ctx=s['context'];pol=s['policy'];status=pol['status']
        assert s['sha256']==hashlib.sha256(s['mountinfo'].encode()).hexdigest()
        count=private_workload.private_snapshot(s['mountinfo'])
        successes=[x for x in records if x.get('private_workload_'+('precondition' if stage=='pre' else 'postcondition')) is True]
        assert len(successes)==1 and successes[0]['mounts']==count
        assert ctx['cgroup']==origin['cgroup'] and ctx['uid']==origin['uid'] and ctx['gid']==origin['gid']
        for n in ['mnt','user','pid','net']:assert (ctx['namespaces'][n]!=origin['namespaces'][n])==(stage=='post' or n in ('mnt','user'))
        assert pol['stage']==stage and status['Uid']==[str(origin['uid'])]*4 and status['Gid']==[str(origin['gid'])]*4
        for n in ['CapInh','CapPrm','CapEff','CapAmb']+(['CapBnd'] if stage=='post' else []):assert len(status[n])==1 and int(status[n][0],16)==0
        assert status['NoNewPrivs']==['0' if stage=='pre' else '1']
        if stage=='pre':assert pol['label']=='vkf-storage-pre-v2 (enforce)'
        else:
            assert pol['label'].endswith(' (enforce)') and sorted(pol['label'][:-10].split('//&'))==['bwrap','unpriv_bwrap']
            proof=successes[0]['private_workload_storage'];assert proof['mountinfo_sha256']==s['sha256']
            charged=[x for x in proof['rows'] if x['result']=='charged-attempt']
            assert len(charged)==1 and charged[0]['path']==m['attempt_root'] and charged[0]['id']==proof['attempt_mount_id']
    return True
