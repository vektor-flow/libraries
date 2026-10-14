"""Development catalogue: standard TeX math plus explicit upright Greek aliases."""
import string
TOKENS={c:'ord' for c in string.ascii_letters+string.digits}
GREEK='alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa varkappa lambda mu nu xi pi varpi rho varrho sigma varsigma tau upsilon phi varphi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega'
TOKENS.update({'\\'+n:'ord' for n in GREEK.split()})
ALIASES={'\\omicron':'o'}
for name,letter in zip('Alpha Beta Epsilon Zeta Eta Iota Kappa Mu Nu Omicron Rho Tau Chi'.split(),'ABEZHIKMNOPTX'):
    ALIASES['\\'+name]=r'\mathrm{'+letter+'}'
TOKENS.update({token:'ord' for token in ALIASES})
TOKENS.update({t:'ord' for t in r'\infty \nabla \partial \ell \hbar \Re \Im \emptyset \aleph'.split()})
TOKENS.update({t:'bin' for t in ['+','-',r'\pm',r'\mp',r'\times',r'\cdot',r'\div',r'\cup',r'\cap',r'\wedge',r'\vee',r'\oplus',r'\otimes']})
TOKENS.update({t:'rel' for t in ['=','<','>',r'\leq',r'\geq',r'\neq',r'\approx',r'\equiv',r'\sim',r'\simeq',r'\in',r'\notin',r'\subset',r'\subseteq',r'\supset',r'\supseteq',r'\to',r'\rightarrow',r'\leftarrow',r'\leftrightarrow',r'\Rightarrow',r'\Leftarrow',r'\Leftrightarrow',r'\mapsto',r'\perp',r'\parallel']})
TOKENS.update({t:'ord' for t in [r'\forall',r'\exists',r'\neg',r'\cdots',r'\ldots',r'\vdots',r'\ddots']})
DELIMITERS={'(':'open',')':'close','[':'open',']':'close',r'\lbrace':'open',r'\rbrace':'close',r'\langle':'open',r'\rangle':'close','|':'ord',r'\Vert':'ord',r'\lfloor':'open',r'\rfloor':'close',r'\lceil':'open',r'\rceil':'close','/':'ord',r'\backslash':'ord'}
TOKENS.update(DELIMITERS);TOKENS[',']='punct';TOKENS[';']='punct';TOKENS[':']='rel';TOKENS['.']='ord'
OPERATORS=r'\sum \prod \coprod \bigcup \bigcap \bigvee \bigwedge \bigsqcup \bigoplus \bigotimes \bigodot \int \iint \iiint \iiiint \oint \oiint \varoiint \fint \sqint \sqiint \ointclockwise \ointctrclockwise \sin \cos \tan \log \ln \exp \lim \max \min \sup \inf \det'.split()
TOKENS.update({t:'op' for t in OPERATORS})
for delimiter,kind in DELIMITERS.items():
    for size in ['big','Big','bigg','Bigg']:
        key=f'@{size}:{delimiter}';TOKENS[key]=kind;ALIASES[key]='\\'+size+delimiter
# Roman letter assets also allow words in case conditions without font loading.
for c in string.ascii_letters+string.digits:
    TOKENS['@roman:'+c]='ord';ALIASES['@roman:'+c]=r'\mathrm{'+c+'}'
# Isolated accent glyphs retain their own baseline, avoiding whole-expression tiles.
for name,code in {'acute':'0013','grave':'0012','ddot':'007F','tilde':'007E','bar':'0016','breve':'0015','check':'0014','hat':'005E','vec':'017E','dot':'005F','mathring':'0017'}.items():
    key='@accent:'+name;TOKENS[key]='ord';ALIASES[key]=r'\mathchar"'+code
for name,start in [('widehat',0x62),('widetilde',0x65)]:
    for n in range(3):
        key=f'@accent:{name}{n}';TOKENS[key]='ord';ALIASES[key]=r'\mathchar"03'+f'{start+n:02X}'
for name in ['braceld','bracerd','bracelu','braceru']:
    TOKENS['@'+name]='ord';ALIASES['@'+name]='\\'+name
for token in [r'\imath',r'\jmath',r'\uparrow',r'\downarrow',r'\updownarrow',r'\Uparrow',r'\Downarrow',r'\Updownarrow',r'\longrightarrow',r'\longleftarrow',r'\longleftrightarrow',r'\Longrightarrow',r'\Longleftarrow',r'\Longleftrightarrow',r'\hookrightarrow',r'\hookleftarrow',r'\nearrow',r'\searrow',r'\nwarrow',r'\swarrow',r'\rightharpoonup',r'\rightharpoondown',r'\leftharpoonup',r'\leftharpoondown',r'\rightleftharpoons']:
    TOKENS[token]='ord' if token in [r'\imath',r'\jmath'] else 'rel'
for name in ['micro','ohm','degree','percent','angstrom']:
    TOKENS['@unit:'+name]='ord';ALIASES['@unit:'+name]='\\unit{\\'+name+'}'
ALIASES['@unit:micro']=r'\SIUnitSymbolMicro'
TOKENS[r'\prime']='ord'
TOKENS['@unit:arcsecond']='ord';ALIASES['@unit:arcsecond']=r'\unit{\arcsecond}'
# amsfonts selects the wider AMS variants once the text-style body exceeds 2 em.
for name,start in [('widehat',0x5B),('widetilde',0x5D)]:
    for n in range(2):
        key=f'@accent:{name}AMS{n}';TOKENS[key]='ord';ALIASES[key]=r'\mathchar\numexpr\symAMSb*256+"'+f'{start+n:02X}'+r'\relax'
TOKENS['@unit:arcminute']='ord';ALIASES['@unit:arcminute']=r'\unit{\arcminute}'
