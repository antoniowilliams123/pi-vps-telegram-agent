#!/usr/bin/env python3
"""Minimal X (Twitter) API v2 client for the account owner. Stdlib only, OAuth 1.0a user context.

  x.py me                         who am I
  x.py search "query" [N]         recent posts matching query (last 7 days), N<=100
  x.py mentions [N]               recent posts mentioning me
  x.py timeline [N]               my own recent posts
  x.py home [N]                   home feed: recent posts from accounts I follow (newest first)
  x.py post "text" [--reply-to ID] --yes    publish (only after the owner approved the exact text)
  x.py delete ID --yes            delete one of my posts

Every call costs pay-per-use credits, so keep N small. Keys: ~/.x_keys (KEY=VALUE).
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = 'https://api.x.com/2'


def load_keys(path='~/.x_keys'):
    with open(os.path.expanduser(path)) as f:
        return dict(l.strip().split('=', 1) for l in f if '=' in l)


def q(s):
    return urllib.parse.quote(str(s), safe='~')


def oauth_header(method, url, params, keys, nonce=None, timestamp=None):
    """OAuth 1.0a HMAC-SHA1 header (RFC 5849). JSON bodies are not signed; query params are."""
    oauth = {'oauth_consumer_key': keys['X_API_KEY'], 'oauth_nonce': nonce or secrets.token_hex(16),
             'oauth_signature_method': 'HMAC-SHA1', 'oauth_timestamp': timestamp or str(int(time.time())),
             'oauth_token': keys['X_ACCESS_TOKEN'], 'oauth_version': '1.0'}
    base_params = '&'.join(f'{q(k)}={q(v)}' for k, v in sorted({**params, **oauth}.items()))
    base = '&'.join([method, q(url), q(base_params)])
    key = f"{q(keys['X_API_SECRET'])}&{q(keys['X_ACCESS_SECRET'])}"
    oauth['oauth_signature'] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return 'OAuth ' + ', '.join(f'{q(k)}="{q(v)}"' for k, v in sorted(oauth.items()))


def call(method, path, params=None, body=None):
    url, params = API + path, params or {}
    full = url + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(full, json.dumps(body).encode() if body else None, method=method,
                                 headers={'Authorization': oauth_header(method, url, params, load_keys()), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f'X API error {e.code}: {e.read().decode()[:800]}')


FIELDS = {'tweet.fields': 'created_at,public_metrics,author_id', 'expansions': 'author_id', 'user.fields': 'username'}


def show(res):
    users = {u['id']: u['username'] for u in res.get('includes', {}).get('users', [])}
    for t in res.get('data', []):
        m = t.get('public_metrics', {})
        print(f"[{t['id']}] @{users.get(t.get('author_id'), '?')} {t.get('created_at', '')}  "
              f"♥{m.get('like_count', 0)} ↻{m.get('retweet_count', 0)} 💬{m.get('reply_count', 0)}\n  {t['text']}\n")
    if not res.get('data'):
        print('(no posts)')


def me():
    return call('GET', '/users/me')['data']


def main(argv):
    cmd, args = (argv[0] if argv else 'help'), argv[1:]
    yes = '--yes' in args
    args = [a for a in args if a != '--yes']
    n = lambda i, d=10: str(max(10, min(100, int(args[i])))) if len(args) > i else str(d)  # X requires 10..100
    if cmd == 'me':
        print(json.dumps(me()))
    elif cmd == 'search':
        show(call('GET', '/tweets/search/recent', {'query': args[0], 'max_results': n(1), **FIELDS}))
    elif cmd in ('mentions', 'timeline'):
        path = f"/users/{me()['id']}/{'mentions' if cmd == 'mentions' else 'tweets'}"
        show(call('GET', path, {'max_results': n(0), **FIELDS}))
    elif cmd == 'home':
        path = f"/users/{me()['id']}/timelines/reverse_chronological"
        show(call('GET', path, {'max_results': n(0), 'exclude': 'replies', **FIELDS}))
    elif cmd == 'post':
        if not yes:
            sys.exit('Refusing to post without --yes. Show the owner the exact text and get explicit approval first.')
        body = {'text': args[0]}
        if '--reply-to' in args:
            body['reply'] = {'in_reply_to_tweet_id': args[args.index('--reply-to') + 1]}
        d = call('POST', '/tweets', body=body)['data']
        print(f"Posted: https://x.com/i/status/{d['id']}")
    elif cmd == 'delete':
        if not yes:
            sys.exit("Refusing to delete without --yes and the owner's explicit approval.")
        print(json.dumps(call('DELETE', f'/tweets/{args[0]}')))
    else:
        print(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
