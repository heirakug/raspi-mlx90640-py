import time
import board
import busio
import adafruit_mlx90640

# I2C 設定
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
mlx = adafruit_mlx90640.MLX90640(i2c)

# リフレッシュレートの設定
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ

# フレームデータの取得
frame = [0] * 768
while True:
    try:
        mlx.getFrame(frame)
        # ここでフレームデータを処理するコードを追加
        print(frame)  # 仮の出力
    except ValueError:
        # データ取得エラー時の処理
        continue
    time.sleep(0.5)
