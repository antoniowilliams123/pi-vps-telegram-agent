#!/usr/bin/env python3
"""Telegram <-> Pi bridge.

Every text message the owner sends in one Telegram group goes to one ongoing Pi session, and Pi's
reply comes back to the group, so the group behaves like the Pi terminal. Stdlib only.

Group commands: /new starts a fresh conversation, /stop cancels the running answer.
Env: PI_TG_TOKEN (bot token), PI_TG_CHAT (group id), PI_TG_OWNER (the only Telegram user obeyed).
"""
import json
import os
import queue
import subprocess
import threading
import time
import urllib.request
import uuid

STATE = os.path.expanduser('~/.pi_telegram_state.json')
TIMEOUT = 30 * 60  # one answer may run tools for a while
CHUNK = 4000  # Telegram caps a message at 4096 chars
MEDIA = ('photo', 'document', 'video', 'voice', 'audio', 'sticker')


def classify(m, chat, owner):
    """Decide what to do with one Telegram message: (action, text)."""
    if m.get('chat', {}).get('id') != chat or m.get('from', {}).get('id') != owner:
        return 'ignore', ''  # only the owner, only in the configured group
    text = (m.get('text') or m.get('caption') or '').strip()
    if text.startswith('/'):
        cmd = text.split()[0].split('@')[0].lower()  # "/new@MyBot" in groups
        if cmd in ('/new', '/stop'):
            return cmd[1:], ''
    if text:
        return 'prompt', text
    if any(k in m for k in MEDIA):
        return 'media', ''
    return 'ignore', ''  # service messages: member joined, title changed


def chunks(text):
    text = text or '(empty reply)'
    return [text[i:i + CHUNK] for i in range(0, len(text), CHUNK)]


class Bridge:
    def __init__(self, token, chat, owner):
        self.api, self.chat, self.owner = f'https://api.telegram.org/bot{token}/', chat, owner
        self.jobs: queue.Queue = queue.Queue()
        self.proc = None  # the running Pi process, so /stop can kill it
        self.state = self.load_state()

    def tg(self, method, **params):
        req = urllib.request.Request(self.api + method, json.dumps(params).encode(), {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=70) as r:
            return json.load(r)['result']

    def say(self, text):
        for part in chunks(text):
            try:
                self.tg('sendMessage', chat_id=self.chat, text=part)
            except Exception as e:
                print('send failed:', e, flush=True)
            time.sleep(1)

    def load_state(self):
        try:
            with open(STATE) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {'offset': 0, 'session': str(uuid.uuid4())}

    def save_state(self):
        with open(STATE, 'w') as f:
            json.dump(self.state, f)

    def run_pi(self, text):
        # --session-id keeps one conversation across separate `pi -p` runs; PI_TG_BRIDGE tells the
        # telegram-mirror extension not to echo this run (the bridge already replies).
        proc = subprocess.Popen(['pi', '-p', '--session-id', self.state['session'], '--', text],
                                cwd=os.path.expanduser('~'), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env={**os.environ, 'PI_TG_BRIDGE': '1'})
        self.proc, out, err, started = proc, '', '', time.time()
        while proc.poll() is None:  # keep "typing..." visible while Pi works
            try:
                self.tg('sendChatAction', chat_id=self.chat, action='typing')
            except Exception:
                pass
            try:
                out, err = proc.communicate(timeout=4)
            except subprocess.TimeoutExpired:
                if time.time() - started > TIMEOUT:
                    proc.kill()
        self.proc = None
        if proc.returncode == 0:
            self.say(out.strip())
        elif proc.returncode < 0:
            self.say('⏹ Stopped.')
        else:
            self.say(f'⚠️ Pi exited with code {proc.returncode}\n{(err or out).strip()[-1500:]}')

    def worker(self):
        while True:
            self.run_pi(self.jobs.get())

    def handle(self, m):
        action, text = classify(m, self.chat, self.owner)
        if action == 'new':
            self.state['session'] = str(uuid.uuid4())
            self.save_state()
            self.say('🆕 Fresh conversation started.')
        elif action == 'stop':
            if self.proc:
                self.proc.kill()
            else:
                self.say('Nothing is running.')
        elif action == 'prompt':
            if self.proc or not self.jobs.empty():
                self.say('⏳ Queued; Pi will get to it after the current answer.')
            self.jobs.put(text)
        elif action == 'media':
            self.say('Text only for now; photos and files are not passed to Pi.')

    def serve(self):
        self.save_state()
        threading.Thread(target=self.worker, daemon=True).start()
        print('bridge up, session', self.state['session'], flush=True)
        while True:
            try:
                updates = self.tg('getUpdates', offset=self.state['offset'], timeout=60, allowed_updates=['message'])
            except Exception as e:
                print('poll failed:', e, flush=True)
                time.sleep(5)
                continue
            for u in updates:
                self.state['offset'] = u['update_id'] + 1  # ack first: a crash never replays a prompt
                self.save_state()
                self.handle(u.get('message') or {})


if __name__ == '__main__':
    Bridge(os.environ['PI_TG_TOKEN'], int(os.environ['PI_TG_CHAT']), int(os.environ['PI_TG_OWNER'])).serve()
