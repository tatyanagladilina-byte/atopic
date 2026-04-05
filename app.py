#!/usr/bin/env python3
"""
Atopic Brand Carousel Slide Generator
Brand: A.T.O.P.I.C — atopic skin care
Canvas: 1080 × 1350 px (4:5 Instagram ratio)
Palette: #EFE7DA background, #3D2B1F text, #8C7B6B subtitle, #B5A898 accent
"""

import os, sys, json, base64, uuid, time, requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ─── CONSTANTS ───────────────────────────────────────────────────────────────────
W, H       = 1080, 1350          # 4:5 Instagram portrait
CANVAS     = (W, H)
PAD        = 96                  # padding matches CSS spec
BG         = (239, 231, 218)     # #EFE7DA
TEXT       = (61,  43,  31)      # #3D2B1F
SUB        = (140, 123, 107)     # #8C7B6B
ACCENT     = (181, 168, 152)     # #B5A898
WHITE      = (255, 255, 255)
BRAND      = "A.T.O.P.I.C"

# ─── FONTS ───────────────────────────────────────────────────────────────────────
FONTS = {
    "regular": [
        "/app/fonts/Cormorant-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ],
    "italic": [
        "/app/fonts/Cormorant-Italic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
    ],
}

def font(style="regular", size=48):
    for p in FONTS.get(style, FONTS["regular"]):
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()

# ─── HELPERS ─────────────────────────────────────────────────────────────────────
def wrap(text, fnt, max_w, draw):
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        bb = draw.textbbox((0,0), test, font=fnt)
        if bb[2]-bb[0] <= max_w:
            cur.append(w)
        else:
            if cur: lines.append(" ".join(cur))
            cur = [w]
    if cur: lines.append(" ".join(cur))
    return lines

def text_h(draw, lines, fnt, gap=8):
    total = 0
    for l in lines:
        bb = draw.textbbox((0,0), l, font=fnt)
        total += (bb[3]-bb[1]) + gap
    return total

def draw_lines(draw, lines, y, fnt, color, gap=8):
    for l in lines:
        bb = draw.textbbox((0,0), l, font=fnt)
        x = (W - (bb[2]-bb[0])) // 2
        draw.text((x, y), l, font=fnt, fill=color)
        y += (bb[3]-bb[1]) + gap
    return y

def draw_spaced(draw, text, y, fnt, color, letter_gap=3):
    spaced = (" "*letter_gap).join(text.upper())
    bb = draw.textbbox((0,0), spaced, font=fnt)
    x = (W - (bb[2]-bb[0])) // 2
    draw.text((x, y), spaced, font=fnt, fill=color)
    return bb[3]-bb[1]

def accent_line(draw, y, width=100):
    x1 = (W-width)//2; x2 = (W+width)//2
    draw.line([(x1,y),(x2,y)], fill=ACCENT, width=1)

def brand_logo(draw, y=None, x_align="center", color=None):
    """Draw spaced brand name. y=None → bottom-center at H-60."""
    color = color or ACCENT
    fnt = font("regular", 18)
    spaced = "  ".join(BRAND)
    bb = draw.textbbox((0,0), spaced, font=fnt)
    tw = bb[2]-bb[0]
    if y is None: y = H - PAD//2 - (bb[3]-bb[1])
    if x_align == "center": x = (W-tw)//2
    elif x_align == "right": x = W - tw - PAD
    else: x = PAD
    draw.text((x,y), spaced, font=fnt, fill=color)

def gradient_bg():
    img = Image.new("RGB", CANVAS, BG)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        f = y/H
        r = int(239 - f*18); g = int(231 - f*20); b = int(218 - f*22)
        draw.line([(0,y),(W,y)], fill=(r,g,b))
    return img

def fetch_img(url):
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"fetch_img error: {e}")
        return None

def crop_to_ratio(img, ratio_w=4, ratio_h=5):
    """Crop PIL image to target aspect ratio, centered."""
    iw, ih = img.size
    target_ratio = ratio_w / ratio_h
    current_ratio = iw / ih
    if current_ratio > target_ratio:          # wider → crop sides
        new_w = int(ih * target_ratio)
        img = img.crop(((iw-new_w)//2, 0, (iw+new_w)//2, ih))
    else:                                      # taller → crop top/bottom
        new_h = int(iw / target_ratio)
        img = img.crop((0, (ih-new_h)//2, iw, (ih+new_h)//2))
    return img.resize(CANVAS, Image.LANCZOS)

def choose_size(title, sizes=(80,68,56,46), max_w=None, draw=None):
    max_w = max_w or (W - PAD*2)
    d = draw or ImageDraw.Draw(Image.new("RGB",(1,1)))
    for s in sizes:
        f = font("regular", s)
        lines = wrap(title, f, max_w, d)
        if len(lines) <= 3:
            return f, lines
    f = font("regular", sizes[-1])
    return f, wrap(title, f, max_w, d)

# ─── COVER SLIDES (3 types) ──────────────────────────────────────────────────────
def create_cover(title, subtitle="", image_url=None, image_data=None):
    """
    Full-bleed 4:5 image with dark bottom overlay and white text.
    Handles image_url (DALL-E) or base64 image_data.
    """
    bg = None
    if image_url:   bg = fetch_img(image_url)
    if bg is None and image_data:
        try:
            raw = base64.b64decode(image_data) if isinstance(image_data, str) else image_data
            bg = Image.open(BytesIO(raw)).convert("RGB")
        except: pass

    if bg is not None:
        bg = crop_to_ratio(bg)
        # Slight blur for elegance
        bg = bg.filter(ImageFilter.GaussianBlur(radius=0.8))
        img = bg
    else:
        # Fallback warm gradient
        img = gradient_bg()
        # Add subtle texture
        draw_tmp = ImageDraw.Draw(img)

    # Bottom gradient overlay (≈60% of height)
    overlay = Image.new("RGBA", CANVAS, (0,0,0,0))
    ov = ImageDraw.Draw(overlay)
    ov_top = int(H * 0.38)
    ov_h   = H - ov_top
    for yo in range(ov_h):
        alpha = int(210 * (yo/ov_h)**0.65)
        ov.line([(0, ov_top+yo),(W, ov_top+yo)], fill=(28,16,8,alpha))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Brand top-right
    brand_logo(draw, y=PAD, x_align="right", color=(210,196,178))

    # --- text block positioned from bottom ---
    BOTTOM_MARGIN = PAD
    TEXT_MAX_W    = W - PAD*2

    sub_fnt   = font("regular", 19)
    spaced_sub = "  ".join(subtitle.upper()) if subtitle else ""
    sub_h_val = 0
    if subtitle:
        bb = draw.textbbox((0,0), spaced_sub, font=sub_fnt)
        sub_h_val = (bb[3]-bb[1]) + 12 + 28   # text + gap + accent

    title_fnt, title_lines = choose_size(title, (76,62,50,42), TEXT_MAX_W, draw)
    title_h_val = text_h(draw, title_lines, title_fnt, gap=10)

    block_h = sub_h_val + title_h_val + 16
    text_y  = H - BOTTOM_MARGIN - block_h
    text_y  = max(text_y, int(H*0.52))   # never above 52% of height

    if subtitle:
        bb = draw.textbbox((0,0), spaced_sub, font=sub_fnt)
        x = (W - (bb[2]-bb[0])) // 2
        draw.text((x, text_y), spaced_sub, font=sub_fnt, fill=(198,180,158))
        text_y += (bb[3]-bb[1]) + 12
        accent_line(draw, text_y, width=70)
        text_y += 28

    draw_lines(draw, title_lines, text_y, title_fnt, WHITE, gap=10)
    return img

# ─── TEXT SLIDE 1: Large spaced text, space-between layout ───────────────────────
def create_text_slide_1(title, subtitle="", slide_number=None):
    """
    CSS equivalent:
      display:flex; flex-direction:column; justify-content:space-between;
      padding:96px; background:#EFE7DA
    Top: slide number + subtitle category
    Center: large spaced/serif title
    Bottom: brand logo
    """
    img = gradient_bg()
    draw = ImageDraw.Draw(img)

    # ── TOP section ──
    top_y = PAD
    if slide_number:
        n_fnt = font("regular", 16)
        draw.text((PAD, top_y), f"0{slide_number}", font=n_fnt, fill=ACCENT)

    if subtitle:
        sub_fnt = font("regular", 18)
        draw_spaced(draw, subtitle, top_y + 2, sub_fnt, SUB, letter_gap=2)

    # ── BOTTOM: brand ──
    brand_logo(draw, color=ACCENT)

    # ── CENTER: large title ──
    TEXT_MAX_W = W - PAD*2
    # Use large spaced text for short titles, smaller for longer
    if len(title) <= 40:
        title_fnt, title_lines = choose_size(title, (88,74,60), TEXT_MAX_W, draw)
        # Apply letter spacing effect by spacing words more
        gap = 14
    else:
        title_fnt, title_lines = choose_size(title, (68,56,46), TEXT_MAX_W, draw)
        gap = 10

    title_h_val = text_h(draw, title_lines, title_fnt, gap=gap)
    title_y = (H - title_h_val) // 2

    # Draw with spaced-caps style
    for line in title_lines:
        # Apply letter spacing by spreading characters
        spaced_line = "  ".join(line.upper())
        bb = draw.textbbox((0,0), spaced_line, font=title_fnt)
        # Check if spaced version fits, else use normal
        if (bb[2]-bb[0]) <= TEXT_MAX_W:
            x = (W - (bb[2]-bb[0])) // 2
            draw.text((x, title_y), spaced_line, font=title_fnt, fill=TEXT)
            title_y += (bb[3]-bb[1]) + gap
        else:
            bb2 = draw.textbbox((0,0), line, font=title_fnt)
            x = (W - (bb2[2]-bb2[0])) // 2
            draw.text((x, title_y), line, font=title_fnt, fill=TEXT)
            title_y += (bb2[3]-bb2[1]) + gap

    return img

# ─── TEXT SLIDE 2: Text + images strip ───────────────────────────────────────────
def create_text_slide_2(title, body="", subtitle="", photo_urls=None, slide_number=None):
    """
    CSS equivalent:
      display:flex; flex-direction:column; align-items:center; gap:96px;
      padding:96px; background:#EFE7DA
    Top section: subtitle + title + body
    Bottom section: 3-photo strip (or placeholders)
    """
    img = gradient_bg()
    draw = ImageDraw.Draw(img)

    # photo strip height
    PHOTO_H   = 340
    PHOTO_TOP = H - PAD - PHOTO_H
    TEXT_AREA_H = PHOTO_TOP - PAD - PAD  # available for text
    TEXT_MAX_W  = W - PAD*2

    # ── TOP: slide number ──
    if slide_number:
        n_fnt = font("regular", 16)
        draw.text((PAD, PAD), f"0{slide_number}", font=n_fnt, fill=ACCENT)

    # ── Text block: subtitle + accent + title + body ──
    sub_fnt  = font("regular", 18)
    spaced_sub = "  ".join(subtitle.upper()) if subtitle else ""
    sub_bb = draw.textbbox((0,0), spaced_sub, font=sub_fnt) if subtitle else (0,0,0,0)
    sub_h_val = (sub_bb[3]-sub_bb[1] + 10 + 24) if subtitle else 0

    title_fnt, title_lines = choose_size(title, (64,52,44,36), TEXT_MAX_W, draw)
    title_h_val = text_h(draw, title_lines, title_fnt, gap=8)

    body_fnt  = font("regular", 30)
    body_lines = wrap(body, body_fnt, TEXT_MAX_W-60, draw)[:3] if body else []
    body_h_val = (text_h(draw, body_lines, body_fnt, gap=8) + 24) if body_lines else 0

    block_total = sub_h_val + title_h_val + 20 + body_h_val
    text_top = PAD + max(0, (TEXT_AREA_H - block_total) // 2) + 30

    y = text_top
    if subtitle:
        x = (W - (sub_bb[2]-sub_bb[0])) // 2
        draw.text((x, y), spaced_sub, font=sub_fnt, fill=SUB)
        y += (sub_bb[3]-sub_bb[1]) + 10
        accent_line(draw, y, width=80)
        y += 24

    y = draw_lines(draw, title_lines, y, title_fnt, TEXT, gap=8)
    y += 20

    if body_lines:
        accent_line(draw, y, width=50)
        y += 24
        draw_lines(draw, body_lines, y, body_fnt, TEXT, gap=8)

    # ── BOTTOM: photo strip (3 columns) ──
    GAP    = 12
    COL_W  = (W - PAD*2 - GAP*2) // 3

    for i in range(3):
        x_start = PAD + i*(COL_W + GAP)
        photo = None
        if photo_urls and i < len(photo_urls) and photo_urls[i]:
            photo = fetch_img(photo_urls[i])

        if photo:
            # Crop to column ratio
            ph_r = photo.width / photo.height
            col_r = COL_W / PHOTO_H
            if ph_r > col_r:
                nw = int(photo.height * col_r)
                photo = photo.crop(((photo.width-nw)//2, 0, (photo.width+nw)//2, photo.height))
            else:
                nh = int(photo.width / col_r)
                photo = photo.crop((0, (photo.height-nh)//2, photo.width, (photo.height+nh)//2))
            photo = photo.resize((COL_W, PHOTO_H), Image.LANCZOS)
            img.paste(photo, (x_start, PHOTO_TOP))
        else:
            # Warm placeholder
            for py in range(PHOTO_H):
                f = py/PHOTO_H
                r = int(225-f*12); g=int(218-f*12); b=int(208-f*12)
                draw.line([(x_start, PHOTO_TOP+py),(x_start+COL_W, PHOTO_TOP+py)], fill=(r,g,b))

    # Thin line above photos
    accent_line(draw, PHOTO_TOP-2, width=W-PAD*2)

    # Brand
    brand_logo(draw, color=ACCENT)

    return img

# ─── FINAL / CTA SLIDE ───────────────────────────────────────────────────────────
def create_final_slide(title, body="", photo_urls=None):
    """
    CSS: justify-content:space-between, padding:96px, background:#EFE7DA
    Top: brand name large
    Center: title + body
    Bottom: 3 photos (if provided) or just text + brand
    """
    img = gradient_bg()
    draw = ImageDraw.Draw(img)

    PHOTO_H   = 310
    PHOTO_TOP = H - PAD - PHOTO_H
    has_photos = bool(photo_urls and any(photo_urls))

    # ── TOP: brand prominent ──
    brand_fnt = font("regular", 24)
    spaced_brand = "  ".join(BRAND)
    bb = draw.textbbox((0,0), spaced_brand, font=brand_fnt)
    x = (W - (bb[2]-bb[0])) // 2
    draw.text((x, PAD), spaced_brand, font=brand_fnt, fill=ACCENT)
    accent_line(draw, PAD + (bb[3]-bb[1]) + 16, width=140)

    # ── CENTER: title + body ──
    TEXT_MAX_W = W - PAD*2
    center_bottom = PHOTO_TOP - PAD if has_photos else H - PAD*3
    center_top    = PAD + (bb[3]-bb[1]) + 60
    center_h      = center_bottom - center_top

    title_fnt, title_lines = choose_size(title, (72,60,48,40), TEXT_MAX_W, draw)
    title_h_val = text_h(draw, title_lines, title_fnt, gap=8)

    body_fnt   = font("italic", 30)
    body_lines = wrap(body, body_fnt, TEXT_MAX_W-80, draw)[:4] if body else []
    body_h_val = (text_h(draw, body_lines, body_fnt, gap=10) + 30) if body_lines else 0

    block_h = title_h_val + body_h_val
    text_y  = center_top + max(0, (center_h - block_h)//2)

    y = draw_lines(draw, title_lines, text_y, title_fnt, TEXT, gap=8)
    if body_lines:
        y += 30
        accent_line(draw, y, width=50)
        y += 28
        draw_lines(draw, body_lines, y, body_fnt, SUB, gap=10)

    # ── BOTTOM: 3 photos or just brand ──
    if has_photos:
        GAP   = 12
        COL_W = (W - PAD*2 - GAP*2) // 3
        for i in range(3):
            x_start = PAD + i*(COL_W + GAP)
            photo = None
            if photo_urls and i < len(photo_urls) and photo_urls[i]:
                photo = fetch_img(photo_urls[i])
            if photo:
                ph_r = photo.width/photo.height
                col_r = COL_W/PHOTO_H
                if ph_r > col_r:
                    nw = int(photo.height*col_r)
                    photo = photo.crop(((photo.width-nw)//2,0,(photo.width+nw)//2,photo.height))
                else:
                    nh = int(photo.width/col_r)
                    photo = photo.crop((0,(photo.height-nh)//2,photo.width,(photo.height+nh)//2))
                photo = photo.resize((COL_W, PHOTO_H), Image.LANCZOS)
                img.paste(photo, (x_start, PHOTO_TOP))
            else:
                for py in range(PHOTO_H):
                    f=py/PHOTO_H; r=int(222-f*10); g=int(215-f*10); b=int(204-f*10)
                    draw.line([(x_start,PHOTO_TOP+py),(x_start+COL_W,PHOTO_TOP+py)], fill=(r,g,b))
        brand_logo(draw, color=ACCENT)
    else:
        brand_logo(draw, color=ACCENT)

    return img

# ─── CAROUSEL GENERATOR ──────────────────────────────────────────────────────────
def generate_carousel(slides_data):
    results = []
    for i, s in enumerate(slides_data):
        stype  = s.get("type", "text_1")
        title  = s.get("title", "")
        body   = s.get("body", "")
        sub    = s.get("subtitle", "")
        snum   = s.get("slide_number", i+1)
        i_url  = s.get("image_url")
        i_data = s.get("image")
        photos = s.get("photo_urls")  # list of 3 URLs for strip

        if stype == "cover":
            img = create_cover(title, sub, i_url, i_data)
        elif stype == "text_2":
            img = create_text_slide_2(title, body, sub, photos, snum)
        elif stype == "final":
            img = create_final_slide(title, body, photos)
        else:  # "text_1" (default)
            img = create_text_slide_1(title, sub, snum)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=92, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        results.append({
            "slide_number": snum,
            "type": stype,
            "image_base64": b64,
            "format": "jpeg"
        })
    return results

# ─── IN-MEMORY IMAGE STORE ───────────────────────────────────────────────────────
_store = {}

def cleanup():
    cut = time.time() - 1800
    for k in [k for k,v in _store.items() if v.get("t",0)<cut]:
        del _store[k]

# ─── FLASK APP ───────────────────────────────────────────────────────────────────
def create_app():
    try:
        from flask import Flask, request, jsonify, Response
        app = Flask(__name__)

        @app.route("/health")
        def health(): return jsonify({"status":"ok","canvas":"1080x1350"})

        @app.route("/slides/<sid>/<int:n>.png")
        def serve(sid, n):
            sess = _store.get(sid)
            if not sess: return "Not found", 404
            data = sess.get(n)
            if not data: return "Slide not found", 404
            return Response(data, mimetype="image/jpeg",
                            headers={"Cache-Control":"no-cache"})

        @app.route("/generate-from-text", methods=["POST"])
        def gen():
            """
            Input JSON:
            {
              "topic": "...",
              "subtitle": "Здоровье кожи",
              "slides": [{"title":"...","body":"..."},...],
              "cover_image_url": "https://..."    ← DALL-E image URL
            }
            Returns:
            { "urls":["..."], "count":N, "session_id":"...", "slides":[...] }
            """
            try:
                cleanup()
                d = request.get_json()
                topic     = d.get("topic","Атопический дерматит")
                subtitle  = d.get("subtitle","Здоровье кожи")
                gpt_slides= d.get("slides", [])
                cover_url = d.get("cover_image_url")

                slides = []
                # Slide 1: Cover
                slides.append({
                    "type":"cover",
                    "title": topic,
                    "subtitle": subtitle,
                    "slide_number": 1,
                    "image_url": cover_url
                })
                total = len(gpt_slides)
                for j, s in enumerate(gpt_slides, 1):
                    if j == total:            # last → final/CTA
                        slides.append({
                            "type":"final",
                            "title": s.get("title",""),
                            "body":  s.get("body",""),
                            "slide_number": j+1
                        })
                    elif j % 3 == 0 and total >= 4:   # every 3rd → with photos (placeholders)
                        slides.append({
                            "type":"text_2",
                            "title": s.get("title",""),
                            "body":  s.get("body",""),
                            "subtitle": subtitle,
                            "slide_number": j+1
                        })
                    else:
                        slides.append({
                            "type":"text_1",
                            "title": s.get("title",""),
                            "subtitle": subtitle,
                            "slide_number": j+1
                        })

                sid     = str(uuid.uuid4())
                results = generate_carousel(slides)
                _store[sid] = {"t": time.time()}

                base = request.host_url.rstrip("/")
                urls = []
                for r in results:
                    raw = base64.b64decode(r.pop("image_base64"))
                    _store[sid][r["slide_number"]] = raw
                    url = f"{base}/slides/{sid}/{r['slide_number']}.png"
                    r["url"] = url
                    urls.append(url)

                return jsonify({"urls":urls,"count":len(results),
                                "session_id":sid,"slides":results})
            except Exception as e:
                import traceback
                return jsonify({"error":str(e),"trace":traceback.format_exc()}), 500

        return app
    except ImportError:
        return None

app = create_app()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        port = int(os.environ.get("PORT",5000))
        app.run(host="0.0.0.0", port=port)
