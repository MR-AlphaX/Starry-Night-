# this for paint Starry Night for van gouch  by Ahamed Hossam .......
from pathlib import Path
import math
import random
import sys

import pygame
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
IMAGE_PATH = HERE / "stars.webp"

# Tweak these:
WINDOW_WIDTH = 720
WINDOW_HEIGHT = 720
PAINT_WIDTH = 1070            # Higher = more detail, but slower
STROKES_PER_FRAME = 88      # Lower = slower animation; higher = faster
SEED = 10
BACKGROUND = (5, 16, 42)


def clamp(value, low, high):
    return max(low, min(high, value))


def sample_color(image, x, y):
    return image.getpixel((clamp(int(x), 0, image.width - 1),
                           clamp(int(y), 0, image.height - 1)))


def make_strokes(image):
    """Create a multi-scale set of colored brush marks sampled from the image."""
    rng = random.Random(SEED)
    w, h = image.size
    strokes = []

    # A blurred image supplies broad underpainting strokes; the original image
    # supplies smaller, sharper marks for the final detail pass.
    broad = image.filter(ImageFilter.GaussianBlur(15))
    medium = image.filter(ImageFilter.GaussianBlur(6))

    # Broad strokes first, then medium, then small highlight/detail strokes.
    layers = [
        # spacing, length range, width range, source image
        (12, (12, 30), (5, 11), broad),
        (6,  (7, 20),  (3, 7),  medium),
        (3,  (3, 11),  (1, 4),  image),
    ]

    for spacing, lengths, widths, source in layers:
        for y in range(0, h, spacing):
            for x in range(0, w, spacing):
                # Small jitter prevents a visible grid.
                px = x + rng.uniform(-spacing * 0.45, spacing * 0.45)
                py = y + rng.uniform(-spacing * 0.45, spacing * 0.45)

                # Estimate local flow from luminance gradients: strokes tend to
                # run along contours instead of always following a grid.
                x0, y0 = int(clamp(px, 1, w - 2)), int(clamp(py, 1, h - 2))
                c_l = sample_color(source, x0 - 1, y0)
                c_r = sample_color(source, x0 + 1, y0)
                c_u = sample_color(source, x0, y0 - 1)
                c_d = sample_color(source, x0, y0 + 1)
                lum = lambda c: 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2]
                gx = lum(c_r) - lum(c_l)
                gy = lum(c_d) - lum(c_u)
                # Tangent to the local gradient; add a little variation.
                angle = math.atan2(gy, gx) + math.pi / 2
                angle += rng.uniform(-0.62, 0.62)

                length = rng.uniform(*lengths)
                width = rng.uniform(*widths)
                color = sample_color(source, px, py)

                # Slight color variation creates the uneven pigment of brushwork.
                delta = rng.randint(-15, 15)
                color = tuple(int(clamp(ch + delta, 0, 255)) for ch in color)
                strokes.append((px, py, length, width, angle, color, rng.random()))

    rng.shuffle(strokes)
    # Shuffle within layers would mix detail too early; sort by width descending
    # so broad underpainting marks appear first, with detail accumulating later.
    strokes.sort(key=lambda s: s[3], reverse=True)
    return strokes


def draw_brush(surface, stroke, scale_x, scale_y, rng):
    x, y, length, width, angle, color, texture = stroke
    cx, cy = x * scale_x, y * scale_y
    half = length * scale_x / 2
    thick = max(1, width * scale_y)

    dx = math.cos(angle) * half
    dy = math.sin(angle) * half
    # A short, slightly curved mark made from several connected segments.
    bend = rng.uniform(-2.2, 2.2) * scale_y
    p1 = (int(cx - dx), int(cy - dy))
    pm = (int(cx + bend * math.cos(angle + math.pi/2)),
          int(cy + bend * math.sin(angle + math.pi/2)))
    p2 = (int(cx + dx), int(cy + dy))

    # Slightly dark edge underpainting plus the main pigment.
    shadow = tuple(int(ch * 0.68) for ch in color)
    pygame.draw.lines(surface, shadow, False, [p1, pm, p2], max(1, int(thick + 1)))
    pygame.draw.lines(surface, color, False, [p1, pm, p2], max(1, int(thick)))

    # Tiny bristle streaks in the direction of the mark.
    if width >= 3 and rng.random() < 0.72:
        highlight = tuple(int(clamp(ch + 18, 0, 255)) for ch in color)
        ox = math.cos(angle + math.pi/2) * thick * 0.22
        oy = math.sin(angle + math.pi/2) * thick * 0.22
        pygame.draw.line(surface, highlight,
                         (int(p1[0] + ox), int(p1[1] + oy)),
                         (int(p2[0] + ox), int(p2[1] + oy)),
                         1)


def main():
    if not IMAGE_PATH.exists():
        raise SystemExit(
            f"Can't find {IMAGE_PATH.name}.\n"
            "Put starry_night.webp in the same folder as this script."
        )

    pygame.init()
    original = Image.open(IMAGE_PATH).convert("RGB")
    aspect = original.height / original.width
    paint_w = PAINT_WIDTH
    paint_h = int(paint_w * aspect)
    image = original.resize((paint_w, paint_h), Image.Resampling.LANCZOS)

    # Fit the painting inside the window with margins.
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Starry Night — Ahemd Hosam")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("sans", 16)

    strokes = make_strokes(image)
    rng = random.Random(SEED + 1)
    canvas = pygame.Surface((paint_w, paint_h))
    canvas.fill(BACKGROUND)

    index = 0
    paused = False
    finished = False
    show_reference = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit()
                    return
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    canvas.fill(BACKGROUND)
                    index = 0
                    finished = False
                elif event.key == pygame.K_f:
                    show_reference = not show_reference
                elif event.key == pygame.K_UP:
                    STROKE_RATE = 700
                elif event.key == pygame.K_DOWN:
                    STROKE_RATE = 60

        if not paused and not finished:
            end = min(len(strokes), index + STROKES_PER_FRAME)
            for i in range(index, end):
                draw_brush(canvas, strokes[i], 1, 1, rng)
            index = end
            if index >= len(strokes):
                finished = True

        screen.fill((12, 17, 30))
        sw, sh = screen.get_size()
        margin_x, margin_y = 28, 52
        scale = min((sw - margin_x * 2) / paint_w,
                    (sh - margin_y * 2) / paint_h)
        out_w, out_h = int(paint_w * scale), int(paint_h * scale)
        scaled = pygame.transform.smoothscale(canvas, (out_w, out_h))
        xoff = (sw - out_w) // 2
        yoff = (sh - out_h) // 2
        screen.blit(scaled, (xoff, yoff))

        if show_reference:
            ref = pygame.image.fromstring(original.tobytes(), original.size, "RGB")
            ref = pygame.transform.smoothscale(ref, (out_w, out_h))
            ref.set_alpha(125)
            screen.blit(ref, (xoff, yoff))

        status = "Finished" if finished else ("Paused" if paused else "Painting")
        label = font.render(
            f"{status}  |  {index:,}/{len(strokes):,} ",
            True, (230, 235, 245)
        )
        screen.blit(label, (16, 14))
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()