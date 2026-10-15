import io
import tarfile
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fetch_arxiv_corpus import assemble, unpack

class ArxivCorpusTests(unittest.TestCase):
    def test_full_local_inputs_and_original_comments(self):
        files = {'main.tex': b'Before \\input{chap/one} after.\n% \\input{missing}\n\\begin{verbatim}\\input{missing}\\end{verbatim}',
                 'chap/one.tex': b'One \\input{two}', 'chap/two.tex': b'Two.'}
        text, included, diagnostics = assemble(files, 'main.tex')
        self.assertIn('One Two.\n after.', text)
        self.assertIn('% \\input{missing}', text)
        self.assertIn('\\begin{verbatim}\\input{missing}\\end{verbatim}', text)
        self.assertEqual(included, ['main.tex', 'chap/one.tex', 'chap/two.tex'])
        self.assertEqual(diagnostics, [])

    def test_missing_and_cyclic_inputs_are_not_silently_removed(self):
        text, _, diagnostics = assemble({'main.tex': b'\\input{missing}'}, 'main.tex')
        self.assertEqual(text, '\\input{missing}')
        self.assertEqual(len(diagnostics), 1)
        with self.assertRaisesRegex(ValueError, 'Recursive'):
            assemble({'main.tex': b'\\input{main}'}, 'main.tex')

    def test_archive_paths_and_links_are_rejected(self):
        for name, link in [('../escape.tex', False), ('/escape.tex', False), ('link', True)]:
            raw = io.BytesIO()
            with tarfile.open(fileobj=raw, mode='w') as archive:
                member = tarfile.TarInfo(name)
                if link:
                    member.type = tarfile.SYMTYPE
                    member.linkname = '/tmp/target'
                else:
                    member.size = 1
                archive.addfile(member, None if link else io.BytesIO(b'x'))
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                unpack(raw.getvalue())

if __name__ == '__main__':
    unittest.main()
