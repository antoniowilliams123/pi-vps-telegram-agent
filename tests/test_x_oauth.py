import importlib.util
import re
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('x', Path(__file__).parent.parent / 'skills/x-twitter/scripts/x.py')
x = importlib.util.module_from_spec(spec)
spec.loader.exec_module(x)

# Worked example from Twitter's "Creating a signature" docs (public sample credentials, not real ones).
KEYS = {'X_API_KEY': 'xvz1evFS4wEEPTGEFPHBog', 'X_API_SECRET': 'kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw',
        'X_ACCESS_TOKEN': '370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb',
        'X_ACCESS_SECRET': 'LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE'}


def test_signature_matches_the_published_worked_example():
    header = x.oauth_header('POST', 'https://api.twitter.com/1.1/statuses/update.json',
                            {'status': 'Hello Ladies + Gentlemen, a signed OAuth request!', 'include_entities': 'true'},
                            KEYS, nonce='kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg', timestamp='1318622958')
    sig = re.search(r'oauth_signature="([^"]+)"', header).group(1)
    assert x.urllib.parse.unquote(sig) == 'hCtSmYh+iHYCEqBWrE7C7hYmtUk='


def test_post_and_delete_refuse_without_explicit_approval(monkeypatch):
    monkeypatch.setattr(x, 'call', lambda *a, **k: pytest.fail('must not reach the API'))
    with pytest.raises(SystemExit, match='--yes'):
        x.main(['post', 'hello'])
    with pytest.raises(SystemExit, match='--yes'):
        x.main(['delete', '123'])


def test_post_with_approval_sends_text_and_reply_target(monkeypatch, capsys):
    sent = {}
    monkeypatch.setattr(x, 'call', lambda m, p, params=None, body=None: sent.update(m=m, p=p, body=body) or {'data': {'id': '9'}})
    x.main(['post', 'hi there', '--reply-to', '42', '--yes'])
    assert sent == {'m': 'POST', 'p': '/tweets', 'body': {'text': 'hi there', 'reply': {'in_reply_to_tweet_id': '42'}}}
    assert 'x.com/i/status/9' in capsys.readouterr().out
