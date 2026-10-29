#!/bin/bash
# Install FatterPad's per-game face-button daemon for the steamos user (no root).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
install -D -m 755 "$here/fatterpad-abxy" "$HOME/.local/bin/fatterpad-abxy"
install -D -m 644 "$here/fatterpad-abxy.service" "$HOME/.config/systemd/user/fatterpad-abxy.service"
# Nintendo mode: the owned-games list (PCGamingWiki) and Proton's raw-device switch
install -D -m 755 "$here/prompts-db" "$HOME/.local/bin/prompts-db"
install -D -m 644 "$here/prompts-db.service" "$HOME/.config/systemd/user/prompts-db.service"
install -D -m 644 "$here/prompts-db.timer" "$HOME/.config/systemd/user/prompts-db.timer"
install -D -m 644 "$here/70-fatterpad-nintendo.conf" "$HOME/.config/environment.d/70-fatterpad-nintendo.conf"
for f in fatterpad-abxy prompts-db; do python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read())" "$HOME/.local/bin/$f"; done
systemctl --user daemon-reload
systemctl --user enable fatterpad-abxy.service
systemctl --user enable --now prompts-db.timer
systemctl --user restart fatterpad-abxy.service
sleep 2
systemctl --user is-active fatterpad-abxy.service
journalctl --user -u fatterpad-abxy.service -n 5 --no-pager
