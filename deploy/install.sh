#!/usr/bin/env bash
# Install the bridge, the terminal mirror and the X skill for an existing `pi` user. Run with sudo
# from the repo root. Idempotent: re-running updates the files and restarts the service.
set -euo pipefail
U=pi
H=$(getent passwd "$U" | cut -d: -f6) || { echo "create the '$U' user and install Pi first"; exit 1; }

install -o "$U" -g "$U" -m 700 bridge/pi_telegram.py "$H/pi_telegram.py"
install -d -o "$U" -g "$U" -m 700 "$H/.pi/agent/extensions" "$H/.pi/agent/skills/x-twitter/scripts"
install -o "$U" -g "$U" -m 600 extensions/telegram-mirror.ts "$H/.pi/agent/extensions/"
install -o "$U" -g "$U" -m 600 skills/x-twitter/SKILL.md "$H/.pi/agent/skills/x-twitter/"
install -o "$U" -g "$U" -m 700 skills/x-twitter/scripts/x.py "$H/.pi/agent/skills/x-twitter/scripts/"

if [ ! -f "$H/.pi_telegram" ]; then
  install -o "$U" -g "$U" -m 600 .env.example "$H/.pi_telegram"
  echo "Fill in $H/.pi_telegram, then re-run."; exit 0
fi
# terminal sessions need the same env so the mirror extension can post
for f in .profile .bashrc; do
  grep -q pi_telegram "$H/$f" 2>/dev/null || echo 'set -a; [ -f ~/.pi_telegram ] && . ~/.pi_telegram; set +a' >> "$H/$f"
done

install -m 644 deploy/pi-telegram.service /etc/systemd/system/pi-telegram.service
systemctl daemon-reload
systemctl enable pi-telegram
systemctl restart pi-telegram
systemctl --no-pager status pi-telegram | head -5
