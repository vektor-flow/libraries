// Validation only: resolve unchanged dependencies from the current shared tree.
// Candidate files keep normal production imports; no old implementation copies.
import {registerHooks} from 'node:module';
import {existsSync} from 'node:fs';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
const candidate = fileURLToPath(new URL('./candidate/', import.meta.url));
const repository = resolve(fileURLToPath(new URL('../../../', import.meta.url)));
function resolveSource(specifier, context, nextResolve) {
  if (specifier.startsWith('.') && context.parentURL?.startsWith('file:')) {
    const path = fileURLToPath(new URL(specifier, context.parentURL));
    if (path.startsWith(candidate) && !existsSync(path))
      return nextResolve(pathToFileURL(resolve(repository, path.slice(candidate.length))).href, context);
  }
  return nextResolve(specifier, context);
}
registerHooks({resolve: resolveSource});
