"""Development oracle: retain the PDF's four-decimal font widths for origins.

MuPDF traces quantize Type1 widths to three decimals, accumulating visible drift
in long runs. This reads the original PDF operators instead. It supplies no data
to the independent renderer. Unsupported fonts remain on the trace oracle.
"""
import math
from pypdf import PdfReader
from pypdf.generic import ContentStream


def multiply(a, b):
 aa, ab, ac, ad, ae, af = a
 ba, bb, bc, bd, be, bf = b
 return [aa*ba+ac*bb, ab*ba+ad*bb, aa*bc+ac*bd, ab*bc+ad*bd,
         aa*be+ac*bf+ae, ab*be+ad*bf+af]


def pdf_reference_positions(path, encoding):
 """Decode simple Type1 text, including nested Form XObjects and transforms.

 encoding(font_name) returns a native character-code-to-glyph-name sequence or
 None. Glyph identities still come from independent native font programs.
 """
 reader=PdfReader(path); pages=[]
 identity=[1.,0.,0.,1.,0.,0.]
 for page in reader.pages:
  records=[];height=float(page.mediabox.top)
  def walk(stream, resources, initial_ctm):
   ctm=initial_ctm[:];tm=identity[:];line=identity[:];stack=[]
   font=None;size=0.;spacing=wordspace=rise=leading=0.;hscale=1.
   for args,op in ContentStream(stream,reader).operations:
    if op==b'q':stack.append((ctm[:],font,size,spacing,wordspace,rise,leading,hscale))
    elif op==b'Q':ctm,font,size,spacing,wordspace,rise,leading,hscale=stack.pop()
    elif op==b'cm':ctm=multiply(ctm,list(map(float,args)))
    elif op==b'BT':tm=identity[:];line=identity[:]
    elif op==b'Tf':font=resources['/Font'][args[0]].get_object();size=float(args[1])
    elif op==b'Tm':tm=list(map(float,args));line=tm[:]
    elif op in (b'Td',b'TD'):
     dx,dy=map(float,args)
     if op==b'TD':leading=-dy
     line=multiply(line,[1,0,0,1,dx,dy]);tm=line[:]
    elif op==b'T*':line=multiply(line,[1,0,0,1,0,-leading]);tm=line[:]
    elif op==b'Tc':spacing=float(args[0])
    elif op==b'Tw':wordspace=float(args[0])
    elif op==b'Tz':hscale=float(args[0])/100
    elif op==b'Ts':rise=float(args[0])
    elif op==b'TL':leading=float(args[0])
    elif op==b'Do':
     obj=resources['/XObject'][args[0]].get_object()
     if obj.get('/Subtype')=='/Form':
      walk(obj,obj.get('/Resources',resources),multiply(ctm,list(map(float,obj.get('/Matrix',identity)))))
    elif op in (b'TJ',b'Tj'):
     # Other font types are deliberately not assigned speculative identities.
     name=str(font.get('/BaseFont','')).split('+')[-1].lstrip('/').lower()
     names=encoding(name) if font.get('/Subtype')=='/Type1' else None
     widths=font.get('/Widths');first=int(font.get('/FirstChar',0))
     for word in args[0] if op==b'TJ' else args:
      if isinstance(word,(int,float)) or type(word).__name__ in ('FloatObject','NumberObject'):
       tm=multiply(tm,[1,0,0,1,-float(word)*size*hscale/1000,0]);continue
      codes=word.original_bytes if hasattr(word,'original_bytes') else bytes(word)
      for code in codes:
       matrix=multiply(ctm,tm)
       if names is not None:
        records.append({'identity':(name,names[code]),'x':matrix[4]+matrix[2]*rise,
                        'y':height-matrix[5]-matrix[3]*rise,
                        'size':size*math.hypot(matrix[0]*hscale,matrix[1]*hscale)})
       if widths is not None:
        width=float(widths[code-first])*(float(font.get('/FontMatrix',[.001])[0]))
        tm=multiply(tm,[1,0,0,1,(width*size+spacing+(wordspace if code==32 else 0))*hscale,0])
  walk(page.get_contents(),page['/Resources'],identity)
  pages.append(records)
 return pages
