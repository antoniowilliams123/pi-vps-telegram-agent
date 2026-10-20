---
name: x-twitter
description: Read and post on X (Twitter) as the account owner. Use for searching X, reading mentions, the home feed or the owner's timeline, and drafting and publishing posts or replies.
---

# X (Twitter)

Run `python3 scripts/x.py` from this skill directory (`python3 scripts/x.py help` lists commands).

Rules:
- **Never post, reply or delete without the owner's explicit approval of the exact final text in this conversation.** Show the draft, wait for a clear "yes"/"post it", then run with `--yes`. Editing the text after approval needs a new approval.
- Every API call costs pay-per-use credits (reads about $0.005 per post, posts about $0.015, posts with a link about $0.20). Keep result counts small (10 is the minimum and default), avoid repeat searches, and say so before anything that would read hundreds of posts.
- Posts are limited to 280 characters unless the owner says the account has a longer limit. Count before proposing.
- Never print or reveal the contents of `~/.x_keys`.
