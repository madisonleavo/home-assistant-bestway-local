"""Render the project's original geometric tub icon; no vendor branding."""

from pathlib import Path

from PIL import Image, ImageDraw


def main():
    folder = Path(__file__).resolve().parents[1] / "custom_components/bestway_spa_local/brand"
    folder.mkdir(exist_ok=True)
    for size, filename in [(256, "icon.png"), (512, "icon@2x.png")]:
        scale = size / 256
        image = Image.new("RGBA", (size, size))
        draw = ImageDraw.Draw(image)

        def box(values, factor=scale):
            return tuple(round(value * factor) for value in values)

        draw.rounded_rectangle(box((8, 8, 248, 248)), radius=round(48 * scale), fill="#123b50")
        draw.rounded_rectangle(
            box((45, 114, 211, 206)),
            radius=round(28 * scale),
            fill="#2cb6c9",
            outline="#e8fcff",
            width=round(7 * scale),
        )
        draw.line(box((35, 116, 221, 116)), fill="#e8fcff", width=round(10 * scale))
        for x in (85, 128, 171):
            points = [(x + 7, 93), (x - 6, 79), (x + 7, 64), (x - 6, 49)]
            draw.line(
                [(round(a * scale), round(b * scale)) for a, b in points],
                fill="#e8fcff",
                width=round(7 * scale),
                joint="curve",
            )
        image.save(folder / filename, optimize=True)


if __name__ == "__main__":
    main()
