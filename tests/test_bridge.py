import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'bridge'))
from pi_telegram import Bridge, chunks, classify  # noqa: E402

CHAT, OWNER = -100, 7


def msg(text=None, chat=CHAT, user=OWNER, **extra):
    m = {'chat': {'id': chat}, 'from': {'id': user}, **extra}
    if text is not None:
        m['text'] = text
    return m


def test_only_the_owner_in_the_configured_group_is_obeyed():
    assert classify(msg('rm -rf ~', user=999), CHAT, OWNER) == ('ignore', '')
    assert classify(msg('hello', chat=-555), CHAT, OWNER) == ('ignore', '')
    assert classify(msg('hello'), CHAT, OWNER) == ('prompt', 'hello')


def test_commands_work_with_and_without_the_bot_suffix():
    assert classify(msg('/new'), CHAT, OWNER) == ('new', '')
    assert classify(msg('/stop@MyPiBot'), CHAT, OWNER) == ('stop', '')
    assert classify(msg('/model gpt'), CHAT, OWNER) == ('prompt', '/model gpt')  # unknown commands go to Pi


def test_service_messages_are_silent_and_media_gets_a_notice():
    assert classify(msg(new_chat_members=[{'id': 1}]), CHAT, OWNER) == ('ignore', '')
    assert classify(msg(photo=[{}]), CHAT, OWNER) == ('media', '')
    assert classify(msg(photo=[{}], caption='what is this?'), CHAT, OWNER) == ('prompt', 'what is this?')


def test_long_replies_are_split_under_the_telegram_limit():
    parts = chunks('x' * 9000)
    assert [len(p) for p in parts] == [4000, 4000, 1000]
    assert chunks('') == ['(empty reply)']


def test_new_rotates_the_session_and_prompts_queue_behind_a_running_answer(tmp_path, monkeypatch):
    monkeypatch.setattr('pi_telegram.STATE', str(tmp_path / 'state.json'))
    b = Bridge('TOKEN', CHAT, OWNER)
    said = []
    b.say = said.append
    first = b.state['session']
    b.handle(msg('/new'))
    assert b.state['session'] != first
    b.proc = object()  # pretend Pi is busy
    b.handle(msg('next question'))
    assert b.jobs.get_nowait() == 'next question'
    assert said[-1].startswith('⏳ Queued')
