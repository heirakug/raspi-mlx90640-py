# ヘルスチェックスクリプト（health_check.sh）
#!/bin/bash
if ! pgrep -f "main.py" > /dev/null; then
    systemctl restart thermal_cam.service
fi
