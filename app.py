#!/usr/bin/env python3
"""
Atopic Brand Carousel Slide Generator  v3
Brand: A.T.O.P.I.C — atopic skin care
Canvas: 1080 × 1440 px (3:4)
Specs: pixel-perfect from Figma/CSS export
"""

import os, sys, base64, uuid, time, requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ─── CANVAS & PALETTE ────────────────────────────────────────────────────────
W, H   = 1080, 1440
PAD    = 96           # 96px all sides

# Colours (from Figma)
BG          = (241, 232, 227)   # #F1E8E3
TEXT_DARK   = (61,  43,  31)    # #3D2B1F  – body text on light bg
TEXT_SUB    = (140, 123, 107)   # #8C7B6B  – subtitle
ACCENT_LINE = (181, 168, 152)   # #B5A898  – thin rule / brand
WHITE       = (255, 255, 255)
OVERLAY_COL = (80,  63,  53)    # rgba(80,63,53,0.8) — cover gradient end

BRAND = "A.T.O.P.I.C"

# ─── FONT SETUP ──────────────────────────────────────────────────────────────
FONT_DIR = "/app/fonts"
_FONT_URLS = {
    "CactusClassicalSerif-Regular.ttf":
        "https://github.com/google/fonts/raw/main/ofl/cactusclassicalserif/CactusClassicalSerif-Regular.ttf",
    "NotoSans-Regular.ttf":
        "https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans%5Bwdth%2Cwght%5D.ttf",
}

def _download_fonts():
    os.makedirs(FONT_DIR, exist_ok=True)
    for name, url in _FONT_URLS.items():
        path = f"{FONT_DIR}/{name}"
        if not os.path.exists(path):
            try:
                r = requests.get(url, timeout=30)
                if r.status_code == 200:
                    with open(path, "wb") as f: f.write(r.content)
                    print(f"✅ font: {name}")
            except Exception as e:
                print(f"⚠️  font download {name}: {e}")

_download_fonts()

_FONT_SEARCH = {
    "cactus":  [f"{FONT_DIR}/CactusClassicalSerif-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"],
    "sans":    [f"{FONT_DIR}/NotoSans-Regular.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}

def fnt(family: str, size: int) -> ImageFont.FreeTypeFont:
    for p in _FONT_SEARCH.get(family, _FONT_SEARCH["sans"]):
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

# ─── LOW-LEVEL DRAWING HELPERS ───────────────────────────────────────────────

def _text_w(draw, text: str, f) -> int:
    bb = draw.textbbox((0, 0), text, font=f)
    return bb[2] - bb[0]

def _text_h(draw, text: str, f) -> int:
    bb = draw.textbbox((0, 0), text, font=f)
    return bb[3] - bb[1]

def draw_tracked(draw, text: str, cx: float, y: float,
                 f, color, tracking_px: float = 0,
                 align: str = "center", canvas_w: int = W):
    """
    Draw text with CSS letter-spacing (tracking).
    align: 'center' | 'left' | 'right'
    """
    chars = list(text)
    char_widths = [_text_w(draw, c, f) for c in chars]
    total_w = sum(char_widths) + tracking_px * max(len(chars) - 1, 0)

    if align == "center":
        x = (canvas_w - total_w) / 2
    elif align == "right":
        x = canvas_w - PAD - total_w
    else:
        x = cx

    for c, cw in zip(chars, char_widths):
        draw.text((x, y), c, font=f, fill=color)
        x += cw + tracking_px

def wrap_to_lines(draw, text: str, f, max_w: int) -> list[str]:
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if _text_w(draw, test, f) <= max_w:
            cur.append(w)
        else:
            if cur: lines.append(" ".join(cur))
            cur = [w]
    if cur: lines.append(" ".join(cur))
    return lines

def draw_multiline_tracked(draw, lines: list[str], y: float,
                            f, color, line_h: float,
                            tracking_px: float = 0,
                            align: str = "center") -> float:
    """Draw wrapped lines, return y after last line."""
    for line in lines:
        draw_tracked(draw, line, PAD, y, f, color, tracking_px, align)
        y += line_h
    return y

def choose_font_size(draw, text: str, sizes, max_w: int, family="cactus"):
    """Pick largest size where text fits in ≤3 lines."""
    for s in sizes:
        f = fnt(family, s)
        lines = wrap_to_lines(draw, text, f, max_w)
        if len(lines) <= 3:
            return f, lines, s
    f = fnt(family, sizes[-1])
    return f, wrap_to_lines(draw, text, f, max_w), sizes[-1]

# ─── BACKGROUND & GRADIENT ───────────────────────────────────────────────────

def make_bg() -> Image.Image:
    return Image.new("RGB", (W, H), BG)

def add_cover_overlay(img: Image.Image) -> Image.Image:
    """
    CSS: gradient-to-b from rgba(255,244,222,0) → rgba(80,63,53,0.8) at 86.7%
    Above 86.7% (1248px): linear ramp 0→204 alpha
    Below 86.7%: stays at alpha 204
    """
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    stop_y = int(H * 0.867)   # 1248 px
    r, g, b = OVERLAY_COL

    for y in range(H):
        if y <= stop_y:
            a = int(204 * y / stop_y)
        else:
            a = 204
        draw.line([(0, y), (W, y)], fill=(r, g, b, a))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")

def fetch_img(url: str) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"fetch_img error: {e}")
        return None

def fit_cover_image(photo: Image.Image) -> Image.Image:
    """
    CSS: height 112.5%, top -9.38%  → image is 1620px tall, top cropped by 135px
    Actually we just crop to 3:4 and fill canvas.
    """
    iw, ih = photo.size
    target_ratio = W / H   # 0.75
    current_ratio = iw / ih
    if current_ratio > target_ratio:
        nw = int(ih * target_ratio)
        photo = photo.crop(((iw - nw) // 2, 0, (iw + nw) // 2, ih))
    else:
        nh = int(iw / target_ratio)
        # shift slightly upward (-9.38% of 1440 = -135px)
        shift = int(nh * 0.094)
        top = max(0, (ih - nh) // 2 - shift)
        photo = photo.crop((0, top, iw, top + nh))
    return photo.resize((W, H), Image.LANCZOS)

# ─── SLIDE TYPE 1: COVER ─────────────────────────────────────────────────────
# Figma: full-bleed image + gradient overlay + centered text bottom-up
# Layout (justify-end): brand → 72px gap → title block
#
def create_cover(title: str, image_url: str | None = None,
                  image_data: str | None = None) -> Image.Image:
    # --- background
    img = make_bg()

    # --- full-bleed photo
    photo = None
    if image_url:   photo = fetch_img(image_url)
    if photo is None and image_data:
        try:
            raw = base64.b64decode(image_data) if isinstance(image_data, str) else image_data
            photo = Image.open(BytesIO(raw)).convert("RGB")
        except: pass

    if photo:
        img = fit_cover_image(photo)
    else:
        # subtle warm gradient fallback
        draw_tmp = ImageDraw.Draw(img)
        for y in range(H):
            f = y / H
            r = int(241 - f * 30); g = int(232 - f * 35); b = int(227 - f * 40)
            draw_tmp.line([(0, y), (W, y)], fill=(r, g, b))

    # --- gradient overlay
    img = add_cover_overlay(img)
    draw = ImageDraw.Draw(img)

    # --- typography constants
    TITLE_SIZE    = 80
    TITLE_LH      = 100    # line-height px
    TITLE_TRACK   = 0.8    # letter-spacing px
    BRAND_SIZE    = 40
    BRAND_TRACK   = 2.4
    BRAND_ALPHA   = 153    # 60% of 255
    GAP           = 72     # gap between title block and brand
    BOTTOM_MARGIN = PAD    # 96px from bottom

    title_f = fnt("cactus", TITLE_SIZE)
    brand_f = fnt("sans",   BRAND_SIZE)

    # wrap title
    title_lines = wrap_to_lines(draw, title.upper(), title_f, W - PAD * 2)

    title_block_h = len(title_lines) * TITLE_LH
    brand_h       = _text_h(draw, BRAND, brand_f)

    # total content height: title + gap + brand
    total_h = title_block_h + GAP + brand_h
    content_top = H - BOTTOM_MARGIN - total_h

    # --- draw title (white, uppercase, tracked 0.8px)
    y = content_top
    for line in title_lines:
        draw_tracked(draw, line, PAD, y, title_f, WHITE, TITLE_TRACK, "center")
        y += TITLE_LH

    # --- draw brand (white 60%, tracked 2.4px)
    y += GAP
    brand_color = (255, 255, 255, BRAND_ALPHA)

    # Pillow doesn't apply alpha to text directly on RGB — use RGBA composite
    brand_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(brand_layer)
    draw_tracked(bd, BRAND, PAD, y, brand_f, (255, 255, 255, BRAND_ALPHA),
                 BRAND_TRACK, "center")
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, brand_layer)
    img = img.convert("RGB")

    return img

# ─── SLIDE TYPE 2: TEXT SLIDE (light bg, left-aligned) ───────────────────────
# Layout: number top-left | subtitle | title (large) | body | brand bottom-left
#
def create_text_slide(title: str, body: str = "", subtitle: str = "",
                       slide_number: int | None = None) -> Image.Image:
    img = make_bg()
    draw = ImageDraw.Draw(img)

    MAX_W   = W - PAD * 2
    # sizes: try 80→64→52→40
    title_f, title_lines, title_sz = choose_font_size(
        draw, title.upper(), [80, 64, 52, 40], MAX_W, "cactus")

    TITLE_LH    = int(title_sz * 1.25)
    TITLE_TRACK = 0.8
    BODY_SIZE   = 36
    SUB_SIZE    = 24
    NUM_SIZE    = 20
    BRAND_SIZE  = 22
    BRAND_TRACK = 2.4

    y = PAD

    # slide number — top left
    if slide_number is not None:
        n_f = fnt("sans", NUM_SIZE)
        draw.text((PAD, y), f"0{slide_number}", font=n_f, fill=ACCENT_LINE)

    # subtitle — top center, spaced caps
    if subtitle:
        sub_f = fnt("sans", SUB_SIZE)
        sub_up = subtitle.upper()
        draw_tracked(draw, sub_up, PAD, y + 4, sub_f, TEXT_SUB,
                     tracking_px=2.0, align="center")

    y += 72   # drop after top row

    # thin rule
    draw.line([(PAD, y), (W - PAD, y)], fill=ACCENT_LINE, width=1)
    y += 40

    # title block
    y = draw_multiline_tracked(draw, title_lines, y, title_f, TEXT_DARK,
                                TITLE_LH, TITLE_TRACK, "left")
    y += 40

    # body text
    if body:
        body_f = fnt("sans", BODY_SIZE)
        body_lines = wrap_to_lines(draw, body, body_f, MAX_W)[:5]
        for line in body_lines:
            draw.text((PAD, y), line, font=body_f, fill=TEXT_SUB)
            y += int(BODY_SIZE * 1.55)

    # brand — bottom left
    brand_f = fnt("sans", BRAND_SIZE)
    brand_y = H - PAD - _text_h(draw, BRAND, brand_f)
    draw_tracked(draw, BRAND, PAD, brand_y, brand_f, ACCENT_LINE,
                 BRAND_TRACK, "left")

    return img

# ─── SLIDE TYPE 3: TEXT + PHOTO STRIP ────────────────────────────────────────
# Layout: text top half | 3-column photo strip bottom half
#
def create_photo_slide(title: str, body: str = "", subtitle: str = "",
                        photo_urls: list | None = None,
                        slide_number: int | None = None) -> Image.Image:
    img = make_bg()
    draw = ImageDraw.Draw(img)

    PHOTO_H  = 360
    PHOTO_Y  = H - PAD - PHOTO_H
    MAX_W    = W - PAD * 2
    GAP_COL  = 12
    COL_W    = (MAX_W - GAP_COL * 2) // 3

    title_f, title_lines, title_sz = choose_font_size(
        draw, title.upper(), [64, 52, 44, 36], MAX_W, "cactus")
    TITLE_LH = int(title_sz * 1.25)

    y = PAD
    if slide_number is not None:
        draw.text((PAD, y), f"0{slide_number}",
                  font=fnt("sans", 20), fill=ACCENT_LINE)

    if subtitle:
        draw_tracked(draw, subtitle.upper(), PAD, y + 4,
                     fnt("sans", 22), TEXT_SUB, 2.0, "center")
    y += 64

    draw.line([(PAD, y), (W - PAD, y)], fill=ACCENT_LINE, width=1)
    y += 36

    y = draw_multiline_tracked(draw, title_lines, y, title_f, TEXT_DARK,
                                TITLE_LH, 0.8, "left")
    y += 28

    if body:
        body_f = fnt("sans", 32)
        for line in wrap_to_lines(draw, body, body_f, MAX_W)[:3]:
            draw.text((PAD, y), line, font=body_f, fill=TEXT_SUB)
            y += 48

    # thin rule above photos
    draw.line([(PAD, PHOTO_Y - 16), (W - PAD, PHOTO_Y - 16)],
              fill=ACCENT_LINE, width=1)

    # photo strip
    for i in range(3):
        x0 = PAD + i * (COL_W + GAP_COL)
        photo = None
        if photo_urls and i < len(photo_urls) and photo_urls[i]:
            photo = fetch_img(photo_urls[i])
        if photo:
            ph, pw = photo.height, photo.width
            col_r = COL_W / PHOTO_H
            if pw / ph > col_r:
                nw = int(ph * col_r)
                photo = photo.crop(((pw - nw) // 2, 0, (pw + nw) // 2, ph))
            else:
                nh = int(pw / col_r)
                photo = photo.crop((0, (ph - nh) // 2, pw, (ph + nh) // 2))
            photo = photo.resize((COL_W, PHOTO_H), Image.LANCZOS)
            img.paste(photo, (x0, PHOTO_Y))
        else:
            # warm placeholder
            for py in range(PHOTO_H):
                t = py / PHOTO_H
                r = int(228 - t * 15); g = int(220 - t * 15); b = int(210 - t * 15)
                draw.line([(x0, PHOTO_Y + py), (x0 + COL_W, PHOTO_Y + py)],
                          fill=(r, g, b))

    # brand bottom-right
    brand_f = fnt("sans", 20)
    bw = sum(_text_w(draw, c, brand_f) for c in BRAND) + 2.4 * (len(BRAND) - 1)
    brand_y = H - PAD - _text_h(draw, BRAND, brand_f)
    draw_tracked(draw, BRAND, W - PAD - bw, brand_y, brand_f, ACCENT_LINE, 2.4, "right")

    return img

# ─── SLIDE TYPE 4: FINAL / CTA ───────────────────────────────────────────────
# Layout: brand top-center | large CTA title center | body | brand bottom
#
def create_final_slide(title: str, body: str = "",
                        photo_urls: list | None = None) -> Image.Image:
    img = make_bg()
    draw = ImageDraw.Draw(img)

    PHOTO_H   = 320
    PHOTO_Y   = H - PAD - PHOTO_H
    MAX_W     = W - PAD * 2
    has_photo = bool(photo_urls and any(photo_urls))

    # brand top — large, center
    brand_top_f = fnt("sans", 28)
    draw_tracked(draw, BRAND, PAD, PAD, brand_top_f, TEXT_SUB, 3.0, "center")
    top_brand_h = _text_h(draw, BRAND, brand_top_f)

    # thin rule
    rule_y = PAD + top_brand_h + 20
    draw.line([(PAD, rule_y), (W - PAD, rule_y)], fill=ACCENT_LINE, width=1)

    # title
    bottom_limit = PHOTO_Y - PAD if has_photo else H - PAD * 3
    title_f, title_lines, title_sz = choose_font_size(
        draw, title.upper(), [80, 64, 52, 40], MAX_W, "cactus")
    TITLE_LH = int(title_sz * 1.25)

    body_f = fnt("sans", 34)
    body_lines = wrap_to_lines(draw, body, body_f, MAX_W - 60)[:4] if body else []
    body_h = len(body_lines) * 52 + 40 if body_lines else 0

    total_text_h = len(title_lines) * TITLE_LH + body_h
    center_range = bottom_limit - (rule_y + 40)
    y = rule_y + 40 + max(0, (center_range - total_text_h) // 2)

    y = draw_multiline_tracked(draw, title_lines, y, title_f, TEXT_DARK,
                                TITLE_LH, 0.8, "center")

    if body_lines:
        y += 40
        draw.line([(PAD, y), (W - PAD, y)], fill=ACCENT_LINE, width=1)
        y += 28
        for line in body_lines:
            draw_tracked(draw, line, PAD, y, body_f, TEXT_SUB, 0, "center")
            y += 52

    # photos
    if has_photo:
        GAP_COL = 12
        COL_W = (MAX_W - GAP_COL * 2) // 3
        for i in range(3):
            x0 = PAD + i * (COL_W + GAP_COL)
            photo = fetch_img(photo_urls[i]) if photo_urls and i < len(photo_urls) and photo_urls[i] else None
            if photo:
                ph, pw = photo.height, photo.width
                col_r = COL_W / PHOTO_H
                if pw / ph > col_r:
                    nw = int(ph * col_r)
                    photo = photo.crop(((pw - nw) // 2, 0, (pw + nw) // 2, ph))
                else:
                    nh = int(pw / col_r)
                    photo = photo.crop((0, (ph - nh) // 2, pw, (ph + nh) // 2))
                photo = photo.resize((COL_W, PHOTO_H), Image.LANCZOS)
                img.paste(photo, (x0, PHOTO_Y))

    # brand bottom
    brand_bot_f = fnt("sans", 20)
    brand_y = H - PAD - _text_h(draw, BRAND, brand_bot_f)
    draw_tracked(draw, BRAND, PAD, brand_y, brand_bot_f, ACCENT_LINE, 2.4, "center")

    return img

# ─── CAROUSEL BUILDER ────────────────────────────────────────────────────────

def build_carousel(slides_data: list) -> list[dict]:
    results = []
    for i, s in enumerate(slides_data):
        stype   = s.get("type", "text")
        title   = s.get("title", "")
        body    = s.get("body", "")
        sub     = s.get("subtitle", "")
        num     = s.get("slide_number", i + 1)
        i_url   = s.get("image_url")
        i_data  = s.get("image")
        photos  = s.get("photo_urls")

        if   stype == "cover":  img = create_cover(title, i_url, i_data)
        elif stype == "photo":  img = create_photo_slide(title, body, sub, photos, num)
        elif stype == "final":  img = create_final_slide(title, body, photos)
        else:                   img = create_text_slide(title, body, sub, num)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=93, optimize=True)
        results.append({
            "slide_number": num,
            "type": stype,
            "image_base64": base64.b64encode(buf.getvalue()).decode(),
            "format": "jpeg",
        })
    return results

# ─── IN-MEMORY STORE (30 min TTL) ────────────────────────────────────────────
_store: dict = {}

def _cleanup():
    cut = time.time() - 1800
    for k in [k for k, v in _store.items() if v.get("t", 0) < cut]:
        del _store[k]

# ─── FLASK APP ───────────────────────────────────────────────────────────────
def create_app():
    try:
        from flask import Flask, request, jsonify, Response
    except ImportError:
        return None

    app = Flask(__name__)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "canvas": f"{W}x{H}", "version": "3"})

    @app.route("/slides/<sid>/<int:n>.jpg")
    def serve(sid, n):
        sess = _store.get(sid)
        if not sess: return "Not found", 404
        data = sess.get(n)
        if not data: return "Slide not found", 404
        return Response(data, mimetype="image/jpeg",
                        headers={"Cache-Control": "no-cache"})

    # backward compat
    @app.route("/slides/<sid>/<int:n>.png")
    def serve_png(sid, n):
        return serve(sid, n)

    @app.route("/generate-from-text", methods=["POST"])
    def gen():
        """
        POST body:
        {
          "topic":          "...",
          "subtitle":       "Здоровье кожи",          // optional
          "slides":         [{"title":"...","body":"..."},...],
          "cover_image_url":"https://...",             // DALL-E URL
          "photo_urls":     ["url1","url2","url3"]     // Cloudinary avatars
        }
        """
        try:
            _cleanup()
            d          = request.get_json(force=True)
            topic      = d.get("topic", "Атопический дерматит")
            subtitle   = d.get("subtitle", "Здоровье кожи")
            gpt_slides = d.get("slides", [])
            cover_url  = d.get("cover_image_url")
            cover_data = d.get("cover_image_data")   # base64 from gpt-image-1
            photo_urls = d.get("photo_urls") or []

            slides = []

            # Slide 1 — Cover
            slides.append({
                "type":      "cover",
                "title":     topic,
                "slide_number": 1,
                "image_url": cover_url,
                "image":     cover_data,   # b64 fallback if no URL
            })

            total = len(gpt_slides)
            for j, s in enumerate(gpt_slides, 1):
                if j == total:
                    # last slide → CTA
                    slides.append({
                        "type":  "final",
                        "title": s.get("title", ""),
                        "body":  s.get("body", ""),
                        "slide_number": j + 1,
                        "photo_urls": photo_urls[:3] if photo_urls else None,
                    })
                elif j % 3 == 0 and total >= 4:
                    # every 3rd → photo strip
                    slides.append({
                        "type":      "photo",
                        "title":     s.get("title", ""),
                        "body":      s.get("body", ""),
                        "subtitle":  subtitle,
                        "slide_number": j + 1,
                        "photo_urls": photo_urls[:3] if photo_urls else None,
                    })
                else:
                    slides.append({
                        "type":      "text",
                        "title":     s.get("title", ""),
                        "body":      s.get("body", ""),
                        "subtitle":  subtitle,
                        "slide_number": j + 1,
                    })

            sid     = str(uuid.uuid4())
            results = build_carousel(slides)
            _store[sid] = {"t": time.time()}

            base = request.host_url.rstrip("/")
            urls = []
            for r in results:
                raw = base64.b64decode(r.pop("image_base64"))
                _store[sid][r["slide_number"]] = raw
                r["url"] = f"{base}/slides/{sid}/{r['slide_number']}.jpg"
                urls.append(r["url"])

            return jsonify({
                "urls":       urls,
                "count":      len(results),
                "session_id": sid,
                "slides":     results,
            })

        except Exception as e:
            import traceback
            return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

    return app


app = create_app()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
