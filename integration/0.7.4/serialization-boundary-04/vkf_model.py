"""Small, fail-closed interpreter-by-translation for this candidate's VKF subset.
It tests source algorithms under Python primitive semantics, NOT the VKF backend.
Only comments, declared signatures and explicit syntax below are accepted.
"""
import json
import re
from types import SimpleNamespace as Record


def utf8_at(s,p):
    if p>=len(s.encode('utf-8')): return ''
    return s.encode('utf-8')[p:].decode('utf-8')[0]

def utf8_advance(s,p): return p+len(utf8_at(s,p).encode('utf-8'))


def translate(source, dependencies=None):
    ns=dict(Record=Record,num=float,int=int,str=str,chr=chr,abs=abs,len=len,
            vkf_string_eof=lambda s,p:p>=len(s.encode('utf-8')),
            vkf_string_peek_scalar=utf8_at,vkf_utf8_advance=utf8_advance)
    ns.update(dependencies or {})
    strings={}
    assertions=[]
    def expression(s):
        def quoted(m):
            key='LITERAL_'+str(len(strings))
            strings[key]=json.loads(m[0]);return key
        s=re.sub(r'"(?:\\.|[^"\\])*"',quoted,s)
        s=s.replace('/\\',' and ').replace('\\/',' or ').replace('~=','!=')
        s=re.sub(r'(?<![<>=!])=(?!=)','==',s).replace('~','not ')
        s=re.sub(r'\btrue\b','True',s);s=re.sub(r'\bfalse\b','False',s)
        s=re.sub(r'\|([^|]+)\|',r'abs(\1)',s)
        s=re.sub(r'\.\(([^()]*)\)',r'[\1]',s)
        s=re.sub(r'([\w.]+)\.length\(\)',r'len(\1)',s)
        s=re.sub(r'\[([^\[\]:]+):([^\[\]]+)\]',r'([\1]*int(\2))',s)
        if re.match(r'^\(\w+:',s):
            s='Record'+s
            s=re.sub(r'(?<=[(,])(\w+):',r'\1=',s)
        return s.replace('&','+').strip()
    def statement(s):
        s=s.strip()
        if '?!' in s:
            expr,label=s.split('?!',1)
            label=json.loads(label.strip());assertions.append(label)
            return 'assert '+expression(expr)+', '+repr(label)
        if s.startswith('@:'): return 'return '+expression(s[2:])
        if s=='@>': return 'continue'
        if s=='@|': return 'break'
        if '?>' in s:
            condition,body=s.split('?>',1)
            return 'while '+expression(condition)+':'+(' '+statement(body) if body.strip() else '')
        if '?' in s:
            condition,body=s.split('?',1)
            return 'if '+expression(condition)+':'+(' '+statement(body) if body.strip() else '')
        s=re.sub(r'^\[(str|int|num)\] ','',s)
        s=s.lstrip('.')
        if ':' not in s: raise ValueError('Unsupported statement '+s)
        target,expr=s.split(':',1)
        return expression(target)+' = '+expression(expr)
    lines=[]
    for line in source.splitlines():
        if not line.strip() or line.lstrip().startswith('#'): continue
        if re.match(r'^\w+:\(',line) or re.match(r'^\w+:\.',line): continue
        signature=re.match(r'^(\w+)\(([^)]*)\)->(?:\[\w+\]|\w+):(.*)$',line)
        if signature:
            name,args,body=signature.groups()
            args=','.join(arg.split(':')[0] for arg in args.split(',') if arg)
            lines.append('def '+name+'('+args+'):')
            if body.strip():
                if body.strip().startswith('@:'):lines.append('    '+statement(body))
                else:lines.append('    return '+expression(body))
            continue
        # Scalar iteration is the sole special lower-level source construct.
        if line.strip()=='c >>':
            lines.append('    for scalar_codepoint in map(ord,c):');continue
        if line.strip()=='.v:int($)':lines.append('        v = int(scalar_codepoint)');continue
        if line.strip()=='$':lines.append('        pass');continue
        indent=len(line)-len(line.lstrip())
        if not indent: raise ValueError('Unsupported top-level '+line)
        lines.append(' '*indent+statement(line))
    ns.update(strings)
    output='\n'.join(lines)+'\n'
    exec(compile(output,'<source-derived VKF model>','exec'),ns)
    return Record(**ns),output,assertions
