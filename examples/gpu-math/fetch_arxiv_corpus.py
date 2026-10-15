"""Preserve versioned arXiv projects/PDFs and assemble local TeX inputs for auditing.

No source is executed. Original downloads and every extracted file keep hashes.
The supplied PDF, rather than a locally repaired compilation, is the oracle.
"""
import argparse
import gzip
import hashlib
import io
import json
import re
import tarfile
import urllib.request
from pathlib import Path, PurePosixPath

PAPERS = json.loads(Path(__file__).with_name('arxiv-corpus.json').read_text())
LIMIT = 32 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unpack(raw):
    files = {}
    try:
        archive = tarfile.open(fileobj=io.BytesIO(raw))
    except tarfile.ReadError:
        text = gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw
        if len(text) > LIMIT:
            raise ValueError('Source exceeds extraction limit')
        return {'source.tex': text}
    with archive:
        total = 0
        for member in archive:
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or member.issym() or member.islnk():
                raise ValueError('Unsafe archive member: ' + member.name)
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError('Unsupported archive member: ' + member.name)
            total += member.size
            if total > LIMIT or len(files) >= 4096:
                raise ValueError('Source exceeds extraction limit')
            key = str(path)
            if key in files:
                raise ValueError('Duplicate archive member: ' + key)
            files[key] = archive.extractfile(member).read()
    return files


def assemble(files, entry):
    included, diagnostics = [], []
    def visit(name, chain):
        if name in chain or len(chain) > 32:
            raise ValueError('Recursive TeX input: ' + name)
        included.append(name)
        text = files[name].decode('utf-8')
        # Protect comments/verbatim from input substitution. Retain their bytes.
        pattern = r'\\begin\{verbatim\}[\s\S]*?\\end\{verbatim\}|\\verb\*?([^A-Za-z\s])[^\n]*?\1|\\(?:input|include|subfile)\s*\{([^{}]+)\}|\\.|%[^\n]*'
        def replace(match):
            if match[2] is None:
                return match[0]
            requested = PurePosixPath(match[2])
            if requested.is_absolute() or '..' in requested.parts:
                raise ValueError('Unsafe TeX input: ' + str(requested))
            candidates = [str(PurePosixPath(name).parent / requested), str(requested)]
            target = next((p for base in candidates for p in [base, base + '.tex'] if p in files), None)
            if target is None:
                diagnostics.append('Unresolved TeX input: ' + match[2])
                return match[0]
            # TeX inserts an endline at file EOF, even without a physical newline.
            return visit(target, chain + [name]).rstrip('\n') + '\n'
        return re.sub(pattern, replace, text)
    text = visit(entry, [])
    return text, included, diagnostics


def fetch(output, cache=None):
    output.mkdir()
    records = []
    for paper in PAPERS:
        identifier, entry = paper['identifier'], paper['entry']
        name = identifier.replace('/', '-')
        folder = output / name
        folder.mkdir()
        downloads = {}
        for kind, filename in [('src', 'original-source.bin'), ('pdf', 'source.pdf')]:
            url = 'https://arxiv.org/' + kind + '/' + identifier
            cached = cache / (identifier.split('/')[-1] + '.' + kind) if cache else None
            if cached and not cached.exists() and kind == 'src':
                cached = cached.with_suffix('.src')
            if cached and cached.exists():
                raw = cached.read_bytes()
            else:
                with urllib.request.urlopen(url, timeout=45) as response:
                    raw = response.read(LIMIT + 1)
            if len(raw) > LIMIT or (kind == 'pdf' and not raw.startswith(b'%PDF-')):
                raise ValueError('Invalid or oversized download: ' + url)
            (folder / filename).write_bytes(raw)
            if sha(raw) != paper['reviewedHashes'][kind]:
                raise ValueError('Downloaded bytes differ from reviewed hash; preserved for review: ' + url)
            downloads[kind] = {'url': url, 'sha256': sha(raw), 'bytes': len(raw)}
        files = unpack((folder / 'original-source.bin').read_bytes())
        for path, raw in files.items():
            dest = folder / 'original' / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        text, included, diagnostics = assemble(files, entry)
        (folder / 'source.tex').write_text(text)
        records.append({'name': name, 'arxiv': identifier, 'entry': entry,
                        'url': 'https://arxiv.org/abs/' + identifier,
                        'downloads': downloads, 'sha256': sha(text.encode()),
                        'includedFiles': included, 'assemblyDiagnostics': diagnostics,
                        'files': {path: {'sha256': sha(raw), 'bytes': len(raw)} for path, raw in files.items()},
                        'scope': 'Complete project and original PDF; source.tex only substitutes local inputs. No macro/package removal, repaired PDF, or source license reassignment.'})
        (output / 'sources.json').write_text(json.dumps(records, indent=2) + '\n')
        print(name, len(files), 'files', len(text), 'characters', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--cache', type=Path)
    args = parser.parse_args()
    fetch(args.output, args.cache)
