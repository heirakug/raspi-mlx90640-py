#!/usr/bin/env python3
# mlx90640_thermal_cam_optimized_ravel.py
import numpy as np
import pygame
import argparse
import board
import busio
import adafruit_mlx90640
import matplotlib.pyplot as plt
from time import sleep

# コマンドライン引数の設定
parser = argparse.ArgumentParser()
parser.add_argument('--min', type=float, default=20.0, help='Minimum temperature (C)')
parser.add_argument('--max', type=float, default=40.0, help='Maximum temperature (C)')
parser.add_argument('--rotate', type=int, default=3, choices=[0,1,2,3], help='Image rotation (90° steps)')
parser.add_argument('--cmap', default='jet', help='Color map (viridis, plasma, inferno, magma, cividis)')
args = parser.parse_args()

# センサー初期化
def initialize_sensor():
    try:
        i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000)
        mlx = adafruit_mlx90640.MLX90640(i2c)
        mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_8_HZ
        print("MLX90640 initialized successfully")
        return mlx
    except ValueError:
        print("Sensor initialization failed. Check I2C connections.")
        exit(1)

# Pygame表示設定
def setup_display():
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    width, height = screen.get_size()
    print(f"Display resolution: {width}x{height}")
    return screen, width, height

# カラーマップ生成
def generate_colormap(cmap_name):
    colormap = plt.get_cmap(cmap_name)
    gradient = np.linspace(0, 1, 256)
    return (colormap(gradient)[:, :3] * 255).astype(np.uint8)

def main():
    mlx = initialize_sensor()
    screen, width, height = setup_display()
    colormap = generate_colormap(args.cmap)
    
    # 1D配列として初期化（24x32=768要素）
    frame_1d = np.zeros(24 * 32, dtype=np.float16)
    clock = pygame.time.Clock()
    
    while True:
        try:
            # 温度データ取得（1D配列として取得）
            mlx.getFrame(frame_1d)
            
            # 2D配列に変換（24行32列）
            frame_2d = frame_1d.reshape(24, 32)
            
            # データ前処理
            frame_clipped = np.clip(frame_2d, args.min, args.max)
            normalized = (frame_clipped - args.min) / (args.max - args.min)
            
            # カラー変換
            color_indices = (normalized * 255).astype(np.uint8)
            rgb_frame = colormap[color_indices]
            
            # 画像回転
            rotated = np.rot90(rgb_frame, k=args.rotate)
            
            # Pygame表示
            surf = pygame.surfarray.make_surface(rotated)
            scaled = pygame.transform.scale(surf, (width, height))
            screen.blit(scaled, (0, 0))
            pygame.display.update()
            
            # FPS制御
            clock.tick(10)
            
        except (ValueError, RuntimeError) as e:
            print(f"Error: {e} - Retrying...")
            sleep(0.1)
            
        # 終了処理
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return

if __name__ == "__main__":
    main()
