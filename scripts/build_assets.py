from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "desktop" / "assets" / "icon.ico"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((2, 2, 254, 254), radius=52, fill="#ffffff", outline="#e8e8e8", width=2)
flame = Image.open(ROOT / "desktop" / "assets" / "flame.png").convert("RGBA")
flame = flame.resize((192, 240), Image.Resampling.LANCZOS)
image.alpha_composite(flame, ((256 - flame.width) // 2, (256 - flame.height) // 2))
image.save(OUTPUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
image.save(ROOT / "desktop" / "assets" / "spark-v4.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(OUTPUT)
