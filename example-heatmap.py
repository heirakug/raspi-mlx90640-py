import time
import board
import busio
import numpy as np
import matplotlib.pyplot as plt
import adafruit_mlx90640

# I2C設定
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
mlx = adafruit_mlx90640.MLX90640(i2c)

# リフレッシュレートの設定
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ

# MLX90640の解像度
HEIGHT = 24
WIDTH = 32
frame = np.zeros((HEIGHT * WIDTH,))

# ヒートマップのセットアップ
plt.ion()  # インタラクティブモード
fig, ax = plt.subplots()
im = ax.imshow(np.zeros((HEIGHT, WIDTH)), cmap="inferno", vmin=0, vmax=40)  # 温度範囲を20～40℃に設定
plt.colorbar(im)

try:
    while True:
        try:
            mlx.getFrame(frame)  # 温度データ取得
            img = np.reshape(frame, (HEIGHT, WIDTH))  # 24×32の配列に変換
            im.set_data(img)  # 画像を更新
            plt.pause(0.1)  # 更新間隔
        except ValueError:
            continue  # データ取得失敗時はリトライ
except KeyboardInterrupt:
    print("終了")
