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
