#!/usr/bin/env python3
"""本番素材と同名・同寸法のダミー画像を生成する。

assets_manifest.txt の各行 (ファイル名, 幅, 高さ, カテゴリ) から、
カテゴリごとに色分けした単色画像を作り、ファイル名を文字として描く。
単色に近い PNG は数 KB 程度になるので、リポジトリと Pages の容量を圧迫しない。

使い方:
    python3 tools/make_dummies.py assets_manifest.txt game/images

依存: Pillow (pip install pillow)
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# カテゴリごとの色 (RGB)。未知のカテゴリは灰色。
COLORS = {
    "bg": (70, 110, 180),
    "chara_a": (230, 140, 40),
    "chara_b": (60, 180, 110),
}
DEFAULT_COLOR = (140, 140, 140)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    manifest = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, w, h, category = [p.strip() for p in line.split(",")]
        width, height = int(w), int(h)
        color = COLORS.get(category, DEFAULT_COLOR)
        img = Image.new("RGB", (width, height), color)
        draw = ImageDraw.Draw(img)
        label = f"{name}\n{width}x{height}\n[{category}]"
        draw.multiline_text((20, 20), label, fill=(255, 255, 255))
        img.save(out_dir / name)
        print(f"dummy: {name} ({width}x{height}, {category})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
