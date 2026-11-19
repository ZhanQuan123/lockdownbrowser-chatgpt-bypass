"""Start mitmweb after a user-approved Sign in with ChatGPT flow.

Open-source SIWC dynamic client registration (PKCE) for this local page reader.
Sign-in appears only when the saved DPAPI session is absent or invalid.
No API key and no ChatGPT browser/session-cookie extraction.
OAuth tokens are saved only as Windows DPAPI-encrypted data.

Requires: pip install 'PyJWT[crypto]'

Usage: python start_mitm_page_reader.py
Optional: MITMWEB_EXE=/path/to/mitmweb, SIWC_MODEL=<authorized-model-slug>
"""

import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlencode, urlparse
import urllib.request
import urllib.error
import uuid
import webbrowser

from reader_auth_cache import read_session, save_session, clear_session, CACHE_FILE

try:
    import jwt
except ImportError as exc:
    raise SystemExit("Install the login dependency: python -m pip install 'PyJWT[crypto]'") from exc

APP_NAME = 'Floating Page Reader'
ISSUER = 'https://auth.openai.com'
AUTH_URL = ISSUER + '/api/accounts/authorize'
TOKEN_URL = ISSUER + '/api/accounts/oauth/token'
JWKS_URL = ISSUER + '/.well-known/jwks.json'
RESOURCE = 'https://api.openai.com/v1'
SCOPES = 'openid profile email offline_access resource.invoke chatgpt.tokens.use.direct'
CONFIG_DIR = Path.home() / '.floating_page_reader'
CONFIG_FILE = CONFIG_DIR / 'registration.json'  # No secret tokens are stored here.
SCRIPT = Path(__file__).with_name('inject_floating_stable_ai_subscription.py')


DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def post_form(url, fields):
    body = urlencode(fields).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST',
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with DIRECT_OPENER.open(req, timeout=35) as result:
            return json.load(result)
    except urllib.error.HTTPError as exc:
        # Do not print the token exchange body; it can contain sensitive fields.
        raise RuntimeError(f'Authorization server rejected the sign-in ({exc.code}).') from exc


def read_registration():
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
            if isinstance(data, dict) and data.get('ext_agent_host_id'):
                return data
        except (ValueError, OSError):
            pass
    return {'ext_agent_host_id': 'urn:uuid:' + str(uuid.uuid4())}


def save_registration(data):
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix('.tmp')
    # Contains registration identity/client mapping only; NEVER access/refresh tokens.
    with open(tmp, 'w', encoding='utf-8') as out:
        json.dump(data, out, indent=2)
    if os.name != 'nt':
        os.chmod(tmp, 0o600)
    os.replace(tmp, CONFIG_FILE)


def login(registration):
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).rstrip(b'=').decode('ascii')
    existing_client = str(registration.get('client_id', ''))
    client_id = existing_client or 'dynamic_agent_client'
    info = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path != '/auth/callback':
                self.send_error(404)
                return
            query = parse_qs(parsed.query)
            if query.get('state', [''])[0] != state:
                self.send_error(400, 'Incorrect sign-in state')
                return
            if info:
                self.send_error(400, 'Already received a response')
                return
            for key in ('code', 'error', 'client_id'):
                info[key] = query.get(key, [''])[0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(b'<!doctype html><title>Sign-in completed</title><p>Sign-in response received. Return to the proxy terminal.</p>')

        def log_message(self, fmt, *args):
            pass  # Never log callback URL: authorization codes are sensitive.

    with HTTPServer(('127.0.0.1', 0), Callback) as server:
        server.timeout = 2
        callback = f'http://127.0.0.1:{server.server_port}/auth/callback'
        args = {
            'client_id': client_id,
            'ext_agent_host_id': registration['ext_agent_host_id'],
            'response_type': 'code',
            'redirect_uri': callback,
            'scope': SCOPES,
            'resource': RESOURCE,
            'state': state,
            'nonce': nonce,
            'code_challenge_method': 'S256',
            'code_challenge': challenge,
        }
        if existing_client:
            if registration.get('email'):
                args['login_hint'] = registration['email']
        else:
            args['agent_name_hint'] = APP_NAME
        url = AUTH_URL + '?' + urlencode(args)
        print('Opening the official ChatGPT sign-in page. Approve the requested plan-usage permission.')
        print('If your browser already uses port 8080 as its proxy, temporarily disable that proxy for sign-in.')
        if not webbrowser.open(url):
            print('Could not open the browser. Open this link in your browser:')
            print(url)  # This request contains state/PKCE challenge, not an access token.
        deadline = time.monotonic() + 240
        while not info and time.monotonic() < deadline:
            server.handle_request()
    if not info:
        raise RuntimeError('Sign-in was not completed.')
    if info.get('error'):
        raise RuntimeError('ChatGPT sign-in was declined: ' + info['error'][:80])
    if not info.get('code'):
        raise RuntimeError('No authorization code was returned.')
    callback_client = info.get('client_id')
    if existing_client:
        if callback_client and callback_client != existing_client:
            raise RuntimeError('Sign-in returned a different client ID.')
        issued_client = existing_client
    else:
        if not callback_client or callback_client == 'dynamic_agent_client':
            raise RuntimeError('OpenAI did not return the new client ID.')
        issued_client = callback_client

    tokens = post_form(TOKEN_URL, {
        'grant_type': 'authorization_code',
        'client_id': issued_client,
        'code': info['code'],
        'code_verifier': verifier,
        'redirect_uri': callback,
        'resource': RESOURCE,
    })
    id_token = tokens.get('id_token')
    if not isinstance(id_token, str) or not id_token:
        raise RuntimeError('Sign-in returned no identity token.')
    # Verify the ID-token signature using the published JWKS, without the browser proxy.
    with DIRECT_OPENER.open(JWKS_URL, timeout=25) as jwks_response:
        jwks = json.load(jwks_response)
    header = jwt.get_unverified_header(id_token)
    if header.get('alg') != 'RS256' or not header.get('kid'):
        raise RuntimeError('Unsupported identity-token signing algorithm.')
    matches = [item for item in jwks.get('keys', []) if item.get('kid') == header['kid']]
    if len(matches) != 1:
        raise RuntimeError('Identity-token signing key was not found.')
    key = jwt.PyJWK.from_dict(matches[0])
    identity = jwt.decode(id_token, key.key, algorithms=['RS256'], issuer=ISSUER,
                          audience=issued_client, leeway=5,
                          options={'require': ['iss', 'aud', 'sub', 'exp', 'iat', 'nonce']})
    if not secrets.compare_digest(str(identity.get('nonce', '')), nonce):
        raise RuntimeError('Sign-in nonce did not match.')
    if registration.get('subject') and identity['sub'] != registration['subject']:
        raise RuntimeError('This account does not match the original registration. Delete the local registration file only if you want to set up a different account.')
    granted = set(str(tokens.get('scope', '')).split())
    if not {'resource.invoke', 'chatgpt.tokens.use.direct'}.issubset(granted):
        raise RuntimeError('ChatGPT plan usage permission was not granted.')
    if not tokens.get('access_token') or not tokens.get('refresh_token'):
        raise RuntimeError('No renewable access token was returned.')
    registration.update({'client_id': issued_client, 'subject': identity['sub'],
                         'email': identity.get('email', '')})
    save_registration(registration)
    return tokens, issued_client


def refresh_session(session):
    """Refresh a cached session before it expires or after an API 401."""
    response = post_form(TOKEN_URL, {
        'grant_type': 'refresh_token',
        'client_id': session['client_id'],
        'refresh_token': session['refresh_token'],
        'resource': RESOURCE,
    })
    access = response.get('access_token')
    rotated = response.get('refresh_token')
    if not access or not rotated:
        raise RuntimeError('Token renewal did not return a complete session.')
    scopes = set(str(response.get('scope', '')).split())
    if scopes and not {'resource.invoke', 'chatgpt.tokens.use.direct'}.issubset(scopes):
        raise RuntimeError('Plan-usage permission was not granted during renewal.')
    renewed = dict(session)
    renewed.update({
        'access_token': access,
        'refresh_token': rotated,
        'expires_at': time.time() + float(response.get('expires_in', 3600)),
    })
    save_session(renewed)  # A refresh token may rotate on every renewal.
    return renewed


def get_or_login_session(registration):
    """Use DPAPI cache where valid; otherwise run interactive OAuth sign-in."""
    session = None if os.getenv('SIWC_FORCE_LOGIN') == '1' else read_session()
    if session and (
        session.get('client_id') != registration.get('client_id')
        or session.get('subject') != registration.get('subject')
    ):
        session = None
        clear_session()
    if session:
        try:
            if float(session['expires_at']) <= time.time() + 120:
                session = refresh_session(session)
            # The models request also checks that the token really works.
            try:
                model, catalog = choose_model(session['access_token'])
            except urllib.error.HTTPError as exc:
                if exc.code not in (401, 403):
                    raise
                session = refresh_session(session)
                model, catalog = choose_model(session['access_token'])
            print('Reused encrypted ChatGPT login cache for this Windows account.')
            return session, model, catalog
        except (RuntimeError, ValueError, urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
            print('Saved login could not be reused; interactive sign-in is required.')
            clear_session()
    tokens, client_id = login(registration)
    session = {
        'access_token': tokens['access_token'],
        'refresh_token': tokens['refresh_token'],
        'client_id': client_id,
        'expires_at': time.time() + float(tokens.get('expires_in', 3600)),
        'subject': registration.get('subject', ''),
    }
    save_session(session)
    model, catalog = choose_model(session['access_token'])
    return session, model, catalog


def choose_model(token):
    req = urllib.request.Request('https://api.openai.com/v1/models',
                                 headers={'Authorization': 'Bearer ' + token})
    with DIRECT_OPENER.open(req, timeout=30) as response:
        catalog = json.load(response)
    models = catalog.get('models', [])
    import re
    allowed = []
    seen = set()
    for model in models if isinstance(models, list) else []:
        if not isinstance(model, dict) or model.get('visibility') != 'list':
            continue
        slug = str(model.get('slug') or '')
        if not re.fullmatch(r'[a-zA-Z0-9._-]{1,96}', slug) or slug in seen:
            continue
        label = str(model.get('display_name') or model.get('name') or slug).strip()[:85]
        # Do not expose any other account data to injected webpage UI.
        allowed.append({'slug': slug, 'label': label or slug})
        seen.add(slug)
    slugs = [m['slug'] for m in allowed]
    selected = os.getenv('SIWC_MODEL', '').strip() or ('gpt-6.1-sol' if 'gpt-6.1-sol' in slugs else (slugs[0] if slugs else ''))
    if selected not in slugs:
        raise RuntimeError('No usable model was returned for this ChatGPT plan, or SIWC_MODEL is not in the list.')
    return selected, allowed


def find_mitmweb():
    if os.getenv('MITMWEB_EXE'):
        path = os.environ['MITMWEB_EXE'].strip('"')
        if os.path.isfile(path) or shutil.which(path):
            return path
        raise RuntimeError('MITMWEB_EXE does not point to an executable.')
    path = shutil.which('mitmweb')
    if path:
        return path
    # Legacy installed location from this user's existing installation.
    winapps = Path(r'C:\Program Files\WindowsApps\8637MaximilianHils.mitmproxy_12.2.2.0_x64__b9jqetyr0hqq6\mitmweb.exe')
    if winapps.is_file():
        return str(winapps)
    raise RuntimeError('mitmweb not found. Add it to PATH or set MITMWEB_EXE to its full path.')


def main():
    if not SCRIPT.exists():
        raise RuntimeError('Put inject_floating_stable_ai_subscription.py in the same folder as this launcher.')
    # Validate the executable first; the proxy still launches only after sign-in succeeds.
    mitmweb = find_mitmweb()
    registration = read_registration()
    save_registration(registration)  # Persist a stable host ID before first sign-in.
    session, model, models = get_or_login_session(registration)
    child_env = os.environ.copy()
    child_env.update({
        'SIWC_ACCESS_TOKEN': session['access_token'],
        'SIWC_REFRESH_TOKEN': session['refresh_token'],
        'SIWC_CLIENT_ID': session['client_id'],
        'SIWC_SUBJECT': session['subject'],
        'SIWC_EXPIRES_AT': str(session['expires_at']),
        'SIWC_MODEL': model,
        'SIWC_MODELS_JSON': json.dumps(models, ensure_ascii=True),
    })
    # Allow mitmweb's separately loaded addon to import reader_auth_cache.py.
    child_env['PYTHONPATH'] = str(SCRIPT.parent) + os.pathsep + child_env.get('PYTHONPATH', '')
    child_env.pop('OPENAI_API_KEY', None)
    print(f'Using account: {registration.get("email") or "ChatGPT account"}; model: {model}')
    print('Starting mitmweb. Web UI: http://127.0.0.1:8081')
    command = [mitmweb, '-s', str(SCRIPT), '--listen-port', '8080', '--web-port', '8081']
    try:
        return subprocess.call(command, env=child_env)
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError, urllib.error.URLError, jwt.PyJWTError) as exc:
        print('Start failed:', exc, file=sys.stderr)
        sys.exit(1)
