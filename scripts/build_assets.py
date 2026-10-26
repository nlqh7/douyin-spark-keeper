from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "desktop" / "assets" / "icon.ico"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((8, 8, 248, 248), radius=56, fill="#303844")
draw.polygon(
    [(131, 43), (136, 92), (111, 126), (105, 158), (118, 181), (143, 185),
     (169, 171), (177, 143), (166, 111), (153, 96), (155, 132), (140, 147)],
    fill="#f07b52",
)
draw.polygon([(90, 93), (73, 129), (71, 165), (89, 197), (121, 211), (94, 184), (85, 151)], fill="#f07b52")
image.save(OUTPUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(OUTPUT)
