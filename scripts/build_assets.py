from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "desktop" / "assets" / "icon.ico"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
flame = Image.open(ROOT / "desktop" / "assets" / "flame.png").convert("RGBA")
flame.thumbnail((220, 250), Image.Resampling.LANCZOS)
image.alpha_composite(flame, ((256 - flame.width) // 2, (256 - flame.height) // 2))
image.save(OUTPUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
image.save(ROOT / "desktop" / "assets" / "spark.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(OUTPUT)
