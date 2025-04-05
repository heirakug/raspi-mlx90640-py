#!/usr/bin/env python3
import time
import numpy as np
import board
import busio
import adafruit_mlx90640
from flask import Flask, jsonify, render_template_string
import threading
import json
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("thermal_app.log"), logging.StreamHandler()]
)
logger = logging.getLogger("thermal_app")

# 設定
MIN_TEMP = 20.0
MAX_TEMP = 40.0
ROTATION = 3  # 0, 1, 2, 3 (90度単位)
UPDATE_INTERVAL = 0.5  # 更新間隔（秒）

# サーマルデータ保存用
thermal_data = {
    "temperature": 0.0,
    "min_temp": MIN_TEMP,
    "max_temp": MAX_TEMP,
    "image": None,
    "timestamp": time.time()
}
data_lock = threading.Lock()

# Flaskアプリ
app = Flask(__name__)

# HTMLテンプレート（インラインで定義）
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Thermal Camera</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .controls { margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 10px; }
        .control-group { margin-right: 15px; }
        .thermal-display { 
            width: 100%; 
            aspect-ratio: 4 / 3;
            position: relative;
            background-color: #000;
            overflow: hidden;
        }
        .thermal-canvas { 
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }
        .stats {
            margin-top: 10px;
            font-size: 18px;
        }
        input, select, button {
            font-size: 16px;
            padding: 5px;
        }
        button {
            cursor: pointer;
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
        }
        button:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Thermal Camera</h1>
        
        <div class="controls">
            <div class="control-group">
                <label for="minTemp">Min Temp: </label>
                <input type="number" id="minTemp" value="20" step="0.5" style="width: 60px;">
            </div>
            <div class="control-group">
                <label for="maxTemp">Max Temp: </label>
                <input type="number" id="maxTemp" value="40" step="0.5" style="width: 60px;">
            </div>
            <div class="control-group">
                <label for="colormap">Color Map: </label>
                <select id="colormap">
                    <option value="jet">Jet</option>
                    <option value="viridis">Viridis</option>
                    <option value="inferno">Inferno</option>
                    <option value="rainbow">Rainbow</option>
                    <option value="grayscale">Grayscale</option>
                </select>
            </div>
            <div class="control-group">
                <label for="rotation">Rotation: </label>
                <select id="rotation">
                    <option value="0">0°</option>
                    <option value="1">90°</option>
                    <option value="2">180°</option>
                    <option value="3" selected>270°</option>
                </select>
            </div>
            <button id="applySettings">Apply</button>
        </div>
        
        <div class="thermal-display">
            <canvas class="thermal-canvas" id="thermalCanvas"></canvas>
        </div>
        
        <div class="stats">
            <div>Max Temperature: <span id="maxTempDisplay">--</span>°C</div>
            <div>Min Temperature: <span id="minTempDisplay">--</span>°C</div>
            <div>Last Update: <span id="lastUpdate">--</span></div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('thermalCanvas');
        const ctx = canvas.getContext('2d');
        let thermalData = null;
        let minTemp = 20;
        let maxTemp = 40;
        let colormap = 'jet';
        let rotation = 3;
        
        // キャンバスサイズ設定
        function resizeCanvas() {
            const container = canvas.parentElement;
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
            if (thermalData) renderThermalImage();
        }
        
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();
        
        // カラーマップ関数
        function getColor(value, map) {
            value = Math.max(0, Math.min(1, value)); // 0-1の範囲に制限
            
            if (map === 'grayscale') {
                const v = Math.floor(value * 255);
                return `rgb(${v},${v},${v})`;
            } else if (map === 'jet') {
                const r = Math.max(0, Math.min(255, Math.floor(255 * 4 * Math.abs(value - 0.75))));
                const g = Math.max(0, Math.min(255, Math.floor(255 * 4 * Math.abs(value - 0.5))));
                const b = Math.max(0, Math.min(255, Math.floor(255 * 4 * Math.abs(value - 0.25))));
                return `rgb(${r},${g},${b})`;
            } else if (map === 'viridis') {
                // 簡易版viridis
                const r = Math.floor(value * value * 255);
                const g = Math.floor(Math.sin(Math.PI * value) * 255);
                const b = Math.floor((1-value) * 200 + 55);
                return `rgb(${r},${g},${b})`;
            } else if (map === 'inferno') {
                const r = Math.floor(Math.pow(value, 0.8) * 255);
                const g = Math.floor(Math.pow(value, 2) * (1-value) * 255);
                const b = Math.floor(0.4 * (1-Math.pow(value, 3)) * 255);
                return `rgb(${r},${g},${b})`;
            } else if (map === 'rainbow') {
                const h = (1 - value) * 240; // 青から赤へ
                const s = 100;
                const l = 50;
                return `hsl(${h},${s}%,${l}%)`;
            }
            
            // デフォルト
            return `rgb(${Math.floor(value*255)},0,${Math.floor((1-value)*255)})`;
        }
        
        // サーマル画像描画
        function renderThermalImage() {
            if (!thermalData || !thermalData.image) return;
            
            const imageData = thermalData.image;
            const height = imageData.length;
            const width = imageData[0].length;
            
            // キャンバスクリア
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // ピクセルサイズ計算
            const pixelWidth = canvas.width / width;
            const pixelHeight = canvas.height / height;
            
            // 画像描画
            for (let y = 0; y < height; y++) {
                for (let x = 0; x < width; x++) {
                    const temp = imageData[y][x];
                    const normalizedTemp = (temp - minTemp) / (maxTemp - minTemp);
                    ctx.fillStyle = getColor(normalizedTemp, colormap);
                    ctx.fillRect(x * pixelWidth, y * pixelHeight, pixelWidth, pixelHeight);
                }
            }
            
            // 温度情報更新
            document.getElementById('maxTempDisplay').textContent = thermalData.temperature.toFixed(1);
            document.getElementById('minTempDisplay').textContent = thermalData.min_displayed.toFixed(1);
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        }
        
        // データ取得
        async function fetchThermalData() {
            try {
                const response = await fetch('/api/thermal');
                if (!response.ok) throw new Error('Network response was not ok');
                thermalData = await response.json();
                renderThermalImage();
            } catch (error) {
                console.error('Error fetching thermal data:', error);
            }
            
            // 定期的に更新
            setTimeout(fetchThermalData, 500);
        }
        
        // 設定適用
        document.getElementById('applySettings').addEventListener('click', function() {
            minTemp = parseFloat(document.getElementById('minTemp').value);
            maxTemp = parseFloat(document.getElementById('maxTemp').value);
            colormap = document.getElementById('colormap').value;
            rotation = document.getElementById('rotation').value;
            
            // 設定をサーバーに送信
            fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    min_temp: minTemp,
                    max_temp: maxTemp,
                    rotation: parseInt(rotation),
                }),
            }).catch(error => console.error('Error updating settings:', error));
        });
        
        // 初期ロード
        document.getElementById('minTemp').value = minTemp;
        document.getElementById('maxTemp').value = maxTemp;
        fetchThermalData();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/thermal')
def get_thermal_data():
    with data_lock:
        # 最小表示温度を計算（データ分析用）
        if thermal_data["image"]:
            min_displayed = float(np.min(thermal_data["image"]))
            thermal_data["min_displayed"] = min_displayed
        return jsonify(thermal_data)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    from flask import request
    try:
        data = request.get_json()
        with data_lock:
            if 'min_temp' in data:
                thermal_data['min_temp'] = float(data['min_temp'])
            if 'max_temp' in data:
                thermal_data['max_temp'] = float(data['max_temp'])
            if 'rotation' in data:
                global ROTATION
                ROTATION = int(data['rotation'])
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

class ThermalSensor:
    def __init__(self):
        self.mlx = None
        self.frame = np.zeros((24, 32), dtype=np.float16)
        self.demo_mode = False
        
        try:
            i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000)
            self.mlx = adafruit_mlx90640.MLX90640(i2c)
            self.mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
            logger.info("Thermal sensor initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize sensor: {e}")
            logger.info("Running in demonstration mode with simulated data")
            self.demo_mode = True
    
    def read_frame(self):
        if self.demo_mode:
            # デモモード：ランダムデータ生成
            with data_lock:
                min_temp = thermal_data["min_temp"] + 5
                max_temp = thermal_data["max_temp"] - 5
            
            frame = np.random.uniform(min_temp, max_temp, (24, 32))
            # 中央部を少し温かく
            center_y, center_x = frame.shape[0] // 2, frame.shape[1] // 2
            frame[center_y-3:center_y+3, center_x-3:center_x+3] += 5.0
            return frame
        else:
            try:
                self.mlx.getFrame(self.frame.ravel())
                return self.frame
            except Exception as e:
                logger.error(f"Error reading from sensor: {e}")
                # エラー時はデモモードに切り替え
                self.demo_mode = True
                return self.read_frame()

def sensor_loop():
    sensor = ThermalSensor()
    logger.info("Sensor loop started")
    
    while True:
        try:
            # センサー読み取り
            frame = sensor.read_frame()
            
            # 回転処理
            with data_lock:
                rotation = ROTATION
            
            # データ回転
            rotated_frame = np.rot90(frame, k=rotation)
            
            # グローバルデータ更新
            with data_lock:
                thermal_data["temperature"] = float(np.max(frame))
                thermal_data["image"] = rotated_frame.tolist()
                thermal_data["timestamp"] = time.time()
            
            time.sleep(UPDATE_INTERVAL)
        except Exception as e:
            logger.error(f"Error in sensor loop: {e}")
            time.sleep(1)  # エラー時は少し待機

if __name__ == "__main__":
    # センサースレッド開始
    sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
    sensor_thread.start()
    
    # Flaskサーバー開始
    logger.info("Starting Flask server on port 5000")
    app.run(host='0.0.0.0', port=5000, threaded=True)