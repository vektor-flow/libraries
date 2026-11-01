// Existing host gh credentials only. JSON requests use stdin; no shell or token
// copies. Errors intentionally omit child stderr and request bodies.
import {spawn} from 'node:child_process';
import {MAX_BYTES, fail} from './metadata.mjs';
export function githubClient(gh = 'gh') {
  return (endpoint, method = 'GET', body) => new Promise((resolve, reject) => {
    const args = ['api', '--method', method, '-H', 'Accept: application/vnd.github+json', endpoint];
    if (body !== undefined) args.push('--input', '-');
    const child = spawn(gh, args, {stdio: ['pipe', 'pipe', 'ignore']});
    const chunks = []; let size = 0, ended = false;
    const timer = setTimeout(() => child.kill('SIGKILL'), 60000);
    function finish(error, value) { if (ended) return; ended = true; clearTimeout(timer); error ? reject(error) : resolve(value); }
    child.on('error', () => finish(new Error('VKF packages: host gh is unavailable')));
    child.stdout.on('data', chunk => { size += chunk.length; if (size > 2 * MAX_BYTES) child.kill('SIGKILL'); else chunks.push(chunk); });
    child.stdin.on('error', () => {});
    child.on('close', code => {
      if (code !== 0 || size > 2 * MAX_BYTES) return finish(new Error(`VKF packages: GitHub ${method} request failed; check host access and repository policy`));
      try { const raw = Buffer.concat(chunks).toString('utf8'); finish(null, raw ? JSON.parse(raw) : null); }
      catch { finish(new Error('VKF packages: invalid GitHub response')); }
    });
    child.stdin.end(body === undefined ? undefined : JSON.stringify(body));
  });
}
