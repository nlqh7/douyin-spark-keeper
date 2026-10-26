from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "desktop" / "assets" / "icon.ico"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((8, 8, 248, 248), radius=50, fill="#111217")
font = ImageFont.truetype("C:/Windows/Fonts/seguisym.ttf", 174)
for offset, color in [((-7, 1), "#20d5ec"), ((7, -1), "#f54c6c"), ((0, 0), "#f7f7f8")]:
    draw.text((128 + offset[0], 125 + offset[1]), "♪", font=font, fill=color, anchor="mm")
image.save(OUTPUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(OUTPUT)
