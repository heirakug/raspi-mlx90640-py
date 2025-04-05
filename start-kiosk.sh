#!/bin/bash
# マウスポインタを非表示
unclutter &

# 数秒待機（X起動の安定のため）
sleep 5

# Chromiumをキオスクモードで起動
chromium-browser --kiosk --no-first-run --disable-infobars --disable-session-crashed-bubble http://localhost:5000
