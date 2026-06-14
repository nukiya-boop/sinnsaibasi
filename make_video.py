#!/usr/bin/env python3
"""
Instagram Reels 1080x1920 動画生成スクリプト
画像にテロップを入れておしゃれな動画を作成する
"""

import os
import subprocess
import textwrap
from PIL import Image, ImageDraw, ImageFont
import numpy as np

FFMPEG = "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
OUT_W, OUT_H = 1080, 1920
FPS = 30
IMAGES_DIR = "/home/user/sinnsaibasi/images"
OUTPUT = "/home/user/sinnsaibasi/output.mp4"

# 使用する画像と各シーンのテロップ設定
SCENES = [
    {
        "image": "DSC07395.jpg",
        "duration": 4.0,
        "telops": [
            {"text": "心斎橋", "size": 90, "y_ratio": 0.12, "delay": 0.3, "sub": False},
            {"text": "大人の隠れ家", "size": 52, "y_ratio": 0.22, "delay": 0.8, "sub": True},
        ],
    },
    {
        "image": "DSC00416.jpg",
        "duration": 4.5,
        "telops": [
            {"text": "職人が選んだ食材", "size": 58, "y_ratio": 0.78, "delay": 0.3, "sub": True},
            {"text": "こだわりのコース料理", "size": 48, "y_ratio": 0.87, "delay": 0.9, "sub": True},
        ],
    },
    {
        "image": "_MG_0912a修.jpg",
        "duration": 4.0,
        "telops": [
            {"text": "特別な夜を", "size": 64, "y_ratio": 0.75, "delay": 0.3, "sub": True},
            {"text": "あなたと", "size": 52, "y_ratio": 0.85, "delay": 0.8, "sub": True},
        ],
    },
    {
        "image": "_MG_0983a修.jpg",
        "duration": 4.0,
        "telops": [
            {"text": "心斎橋の", "size": 56, "y_ratio": 0.76, "delay": 0.3, "sub": True},
            {"text": "「大人デート」ならここへ", "size": 46, "y_ratio": 0.86, "delay": 0.9, "sub": True},
        ],
    },
    {
        "image": "_MG_0989修.jpg",
        "duration": 4.0,
        "telops": [
            {"text": "五感で楽しむ", "size": 64, "y_ratio": 0.76, "delay": 0.3, "sub": True},
            {"text": "一夜限りの体験", "size": 50, "y_ratio": 0.86, "delay": 0.9, "sub": True},
        ],
    },
    {
        "image": "_MG_1126.jpg",
        "duration": 4.0,
        "telops": [
            {"text": "食の芸術", "size": 72, "y_ratio": 0.76, "delay": 0.3, "sub": True},
            {"text": "職人の技が織りなすひと皿", "size": 44, "y_ratio": 0.87, "delay": 0.9, "sub": True},
        ],
    },
    {
        "image": "_MG_1135.jpg",
        "duration": 4.0,
        "telops": [
            {"text": "ご予約はこちら", "size": 58, "y_ratio": 0.80, "delay": 0.3, "sub": True},
        ],
    },
    {
        "image": "心斎橋QR文字入り.jpg",
        "duration": 4.0,
        "telops": [],
    },
]

def fit_image_contain(img: Image.Image, w: int, h: int) -> Image.Image:
    """画像を切らずに黒背景でフィットさせる（letterbox）"""
    bg = Image.new("RGB", (w, h), (0, 0, 0))
    img.thumbnail((w, h), Image.LANCZOS)
    x = (w - img.width) // 2
    y = (h - img.height) // 2
    bg.paste(img, (x, y))
    return bg

def find_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def draw_telop(draw: ImageDraw.ImageDraw, text: str, font_size: int,
               y_center: int, canvas_w: int, alpha_ratio: float = 1.0):
    """テロップを描画（影付き、半透明背景）"""
    font = find_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (canvas_w - tw) // 2

    # 影
    shadow_col = (0, 0, 0, int(200 * alpha_ratio))
    for dx, dy in [(-3, 3), (3, 3), (-3, -3), (3, -3)]:
        draw.text((x + dx, y_center - th // 2 + dy), text, font=font, fill=shadow_col)

    # 本文（白）
    draw.text((x, y_center - th // 2), text, font=font,
              fill=(255, 255, 255, int(255 * alpha_ratio)))


def make_frame(base_img: Image.Image, scene: dict, t: float) -> np.ndarray:
    """1フレーム生成（t=シーン内の経過時間秒）"""
    frame = base_img.copy().convert("RGBA")
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for telop in scene["telops"]:
        elapsed = t - telop["delay"]
        if elapsed < 0:
            continue
        # フェードイン 0.5秒
        fade_in = min(elapsed / 0.5, 1.0)
        # フェードアウト（シーン終了0.5秒前）
        fade_out = min((scene["duration"] - t) / 0.5, 1.0)
        alpha = min(fade_in, max(fade_out, 0.0))
        if alpha <= 0:
            continue

        y = int(OUT_H * telop["y_ratio"])
        draw_telop(draw, telop["text"], telop["size"], y, OUT_W, alpha)

    # グラデーションオーバーレイ（下部を少し暗く）
    grad = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(OUT_H // 3):
        ratio = i / (OUT_H // 3)
        a = int(120 * ratio)
        gd.line([(0, OUT_H - i), (OUT_W, OUT_H - i)], fill=(0, 0, 0, a))

    combined = Image.alpha_composite(frame, grad)
    combined = Image.alpha_composite(combined, overlay)
    return np.array(combined.convert("RGB"))


def main():
    print("動画生成開始...")

    # フレームをパイプでffmpegに渡す
    cmd = [
        FFMPEG, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{OUT_W}x{OUT_H}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "pipe:0",
        "-vcodec", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "fast",
        OUTPUT,
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    try:
        for i, scene in enumerate(SCENES):
            img_path = os.path.join(IMAGES_DIR, scene["image"])
            print(f"  シーン {i+1}/{len(SCENES)}: {scene['image']}")
            raw = Image.open(img_path).convert("RGB")
            base = fit_image_contain(raw, OUT_W, OUT_H)

            n_frames = int(scene["duration"] * FPS)
            for f in range(n_frames):
                t = f / FPS
                frame = make_frame(base, scene, t)
                proc.stdin.write(frame.tobytes())
    finally:
        proc.stdin.close()

    proc.wait()
    if proc.returncode != 0:
        print("ffmpegエラーが発生しました")
    else:
        size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
        print(f"完成！ {OUTPUT} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
