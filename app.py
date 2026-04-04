#!/usr/bin/env python3
"""
Atopic Brand Carousel Slide Generator
Generates Instagram carousel slides matching the A.T.O.P.I.C brand style.

Brand style:
- Background: warm cream #EDE8DF
- Text: dark brown/charcoal #3D2B1F
- Subtitle: warm gray #8C7B6B
- Accent line: muted taupe #B5A898
- Font: Cormorant Garamond (serif, elegant)
- A.T.O.P.I.C logo bottom center or top right
- Instagram size: 1080x1080px
"""

import os
import sys
import json
import base64
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ─── BRAND CONSTANTS ────────────────────────────────────────────────────────────
CANVAS_SIZE     = (1080, 1080)
BG_COLOR        = (237, 232, 223)   # #EDE8DF warm cream
TEXT_COLOR      = (61, 43, 31)      # #3D2B1F dark brown
SUBTITLE_COLOR  = (140, 123, 107)   # #8C7B6B warm gray
ACCENT_COLOR    = (181, 168, 152)   # #B5A898 taupe
WHITE           = (255, 255, 255)
OVERLAY_COLOR   = (50, 35, 25, 180) # dark overlay for cover slides (RGBA)
BRAND_NAME      = "A.T.O.P.I.C"

# ─── FONT PATHS ─────────────────────────────────────────────────────────────────
# On Render.com: install fonts via Dockerfile or startup script
# Fallback to system serif fonts
FONT_PATHS = {
    "regular": [
        "/app/fonts/Cormorant-Regular.ttf",
        "/app/fonts/cormorant_regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ],
    "bold": [
        "/app/fonts/Cormorant-SemiBold.ttf",
        "/app/fonts/cormorant_semibold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    ],
    "italic": [
        "/app/fonts/Cormorant-Italic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    ],
    "light": [
        "/app/fonts/Cormorant-Light.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ],
}

def load_font(style="regular", size=48):
    """Load best available font for the given style and size."""
    for path in FONT_PATHS.get(style, FONT_PATHS["regular"]):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def draw_centered_text(draw, text, y, font, color, canvas_width=1080, letter_spacing=0):
    """Draw centered text, optionally with letter spacing."""
    if letter_spacing > 0:
        # Draw with spacing between letters
        spaced = (" " * letter_spacing).join(text.upper())
        bbox = draw.textbbox((0, 0), spaced, font=font)
        x = (canvas_width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), spaced, font=font, fill=color)
        return bbox[3] - bbox[1]
    else:
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (canvas_width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), text, font=font, fill=color)
        return bbox[3] - bbox[1]

def draw_accent_line(draw, y, width=120, canvas_width=1080):
    """Draw a thin centered accent line."""
    x1 = (canvas_width - width) // 2
    x2 = (canvas_width + width) // 2
    draw.line([(x1, y), (x2, y)], fill=ACCENT_COLOR, width=1)

def draw_brand_logo(draw, canvas_width=1080, canvas_height=1080, position="bottom", color=None):
    """Draw A.T.O.P.I.C brand name."""
    if color is None:
        color = SUBTITLE_COLOR
    font = load_font("regular", 22)
    logo_text = BRAND_NAME
    bbox = draw.textbbox((0, 0), logo_text, font=font)
    text_w = bbox[2] - bbox[0]

    if position == "bottom":
        x = (canvas_width - text_w) // 2
        y = canvas_height - 60
    elif position == "top-right":
        x = canvas_width - text_w - 50
        y = 45
    elif position == "top-left":
        x = 50
        y = 45

    # Letter-spaced brand name
    spaced = "  ".join(BRAND_NAME)
    bbox2 = draw.textbbox((0, 0), spaced, font=font)
    text_w2 = bbox2[2] - bbox2[0]
    if position == "bottom":
        x = (canvas_width - text_w2) // 2
    elif position == "top-right":
        x = canvas_width - text_w2 - 50
    draw.text((x, y), spaced, font=font, fill=color)

# ─── SLIDE TYPE 1: COVER ─────────────────────────────────────────────────────────
def create_cover_slide(title, subtitle="", image_data=None):
    """
    Cover slide: full-bleed image or gradient background,
    dark overlay, white serif text bottom, brand logo top-right.
    """
    img = Image.new("RGB", CANVAS_SIZE, BG_COLOR)

    if image_data:
        try:
            if isinstance(image_data, str):
                # Base64 encoded
                img_bytes = base64.b64decode(image_data)
                bg = Image.open(BytesIO(img_bytes)).convert("RGB")
            else:
                bg = Image.open(BytesIO(image_data)).convert("RGB")

            # Crop to square 1080x1080
            bg_ratio = bg.width / bg.height
            if bg_ratio > 1:
                new_h = bg.height
                new_w = int(bg.height)
                bg = bg.crop(((bg.width - new_w) // 2, 0, (bg.width + new_w) // 2, new_h))
            else:
                new_w = bg.width
                new_h = int(bg.width)
                bg = bg.crop((0, (bg.height - new_h) // 2, new_w, (bg.height + new_h) // 2))
            bg = bg.resize(CANVAS_SIZE, Image.LANCZOS)
            img = bg
        except Exception as e:
            print(f"Image load error: {e}")
    else:
        # Gradient background (cream to darker)
        for y in range(CANVAS_SIZE[1]):
            factor = y / CANVAS_SIZE[1]
            r = int(237 - factor * 40)
            g = int(232 - factor * 45)
            b = int(223 - factor * 50)
            for x in range(CANVAS_SIZE[0]):
                img.putpixel((x, y), (r, g, b))

    # Dark overlay (bottom portion gradient)
    overlay = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_height = 480
    for y_off in range(overlay_height):
        alpha = int(200 * (y_off / overlay_height))
        y_pos = CANVAS_SIZE[1] - overlay_height + y_off
        overlay_draw.line([(0, y_pos), (CANVAS_SIZE[0], y_pos)],
                          fill=(35, 22, 12, alpha))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")

    draw = ImageDraw.Draw(img)

    # Brand logo top-right (white)
    draw_brand_logo(draw, position="top-right", color=(220, 210, 198))

    # Title (large, white, serif, bottom area)
    font_title = load_font("regular", 88)
    font_subtitle = load_font("regular", 30)

    # Subtitle above title
    text_y = CANVAS_SIZE[1] - 300
    if subtitle:
        # Small spaced-caps subtitle
        sub_font = load_font("regular", 22)
        spaced_sub = "  ".join(subtitle.upper())
        bbox = draw.textbbox((0, 0), spaced_sub, font=sub_font)
        x = (CANVAS_SIZE[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x, text_y), spaced_sub, font=sub_font, fill=(200, 185, 168))
        text_y += 45

        # Accent line
        draw_accent_line(draw, text_y, width=80)
        text_y += 25

    # Main title - wrap if needed
    max_w = 900
    lines = wrap_text(title, font_title, max_w, draw)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        x = (CANVAS_SIZE[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x, text_y), line, font=font_title, fill=WHITE)
        text_y += bbox[3] - bbox[1] + 12

    return img

# ─── SLIDE TYPE 2: TEXT ───────────────────────────────────────────────────────────
def create_text_slide(title, body="", subtitle="", slide_number=None):
    """
    Text slide: cream background, small gray subtitle top,
    large serif title center, body text, brand at bottom.
    """
    img = Image.new("RGB", CANVAS_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Slide number (if provided)
    if slide_number:
        num_font = load_font("regular", 18)
        num_text = f"0{slide_number}"
        draw.text((50, 50), num_text, font=num_font, fill=ACCENT_COLOR)

    # Brand logo bottom center
    draw_brand_logo(draw, position="bottom", color=ACCENT_COLOR)

    # Layout: center everything vertically in the usable area
    usable_top = 120
    usable_bottom = CANVAS_SIZE[1] - 100
    usable_height = usable_bottom - usable_top

    # Calculate total content height first
    font_subtitle = load_font("regular", 22)
    font_title = load_font("regular", 82)
    font_body = load_font("regular", 34)

    content_height = 0
    if subtitle:
        content_height += 30 + 20  # text + margin
        content_height += 30       # accent line + margin
    content_height += 100          # title estimate
    if body:
        content_height += 30       # margin before body
        content_height += 60       # body estimate

    start_y = usable_top + (usable_height - content_height) // 2
    y = max(start_y, 200)

    # Subtitle (small, spaced caps, gray)
    if subtitle:
        spaced_sub = "  ".join(subtitle.upper())
        bbox = draw.textbbox((0, 0), spaced_sub, font=font_subtitle)
        x = (CANVAS_SIZE[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), spaced_sub, font=font_subtitle, fill=SUBTITLE_COLOR)
        y += bbox[3] - bbox[1] + 18

        # Accent line
        draw_accent_line(draw, y, width=100)
        y += 30

    # Main title
    max_w = 900
    lines = wrap_text(title, font_title, max_w, draw)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        x = (CANVAS_SIZE[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font_title, fill=TEXT_COLOR)
        y += bbox[3] - bbox[1] + 8

    y += 30

    # Thin accent line below title
    draw_accent_line(draw, y, width=60)
    y += 35

    # Body text (centered, smaller serif)
    if body:
        body_lines = wrap_text(body, font_body, 820, draw)
        for line in body_lines:
            bbox = draw.textbbox((0, 0), line, font=font_body)
            x = (CANVAS_SIZE[0] - (bbox[2] - bbox[0])) // 2
            draw.text((x, y), line, font=font_body, fill=TEXT_COLOR)
            y += bbox[3] - bbox[1] + 10

    return img

# ─── SLIDE TYPE 3: PHOTO STRIP ───────────────────────────────────────────────────
def create_photo_slide(title, body="", subtitle="", photo_data_list=None, slide_number=None):
    """
    Photo slide: cream background, text top half, 3-photo strip bottom half.
    If no photos provided, creates a placeholder.
    """
    img = Image.new("RGB", CANVAS_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)

    if slide_number:
        num_font = load_font("regular", 18)
        draw.text((50, 50), f"0{slide_number}", font=num_font, fill=ACCENT_COLOR)

    draw_brand_logo(draw, position="bottom", color=ACCENT_COLOR)

    font_subtitle = load_font("regular", 22)
    font_title = load_font("regular", 72)
    font_body = load_font("regular", 30)

    y = 160

    # Subtitle
    if subtitle:
        spaced_sub = "  ".join(subtitle.upper())
        bbox = draw.textbbox((0, 0), spaced_sub, font=font_subtitle)
        x = (CANVAS_SIZE[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), spaced_sub, font=font_subtitle, fill=SUBTITLE_COLOR)
        y += bbox[3] - bbox[1] + 18
        draw_accent_line(draw, y, width=100)
        y += 28

    # Title
    lines = wrap_text(title, font_title, 900, draw)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        x = (CANVAS_SIZE[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font_title, fill=TEXT_COLOR)
        y += bbox[3] - bbox[1] + 8

    y += 20
    draw_accent_line(draw, y, width=60)
    y += 28

    # Body
    if body:
        body_lines = wrap_text(body, font_body, 780, draw)
        for line in body_lines[:3]:  # max 3 lines before photos
            bbox = draw.textbbox((0, 0), line, font=font_body)
            x = (CANVAS_SIZE[0] - (bbox[2] - bbox[0])) // 2
            draw.text((x, y), line, font=font_body, fill=TEXT_COLOR)
            y += bbox[3] - bbox[1] + 8

    # ── Photo strip (3 columns) ──────────────────────────────────────────────
    strip_top = 620
    strip_height = 370
    strip_bottom = strip_top + strip_height
    gap = 12
    margin = 50
    col_w = (CANVAS_SIZE[0] - 2 * margin - 2 * gap) // 3

    for i in range(3):
        x_start = margin + i * (col_w + gap)

        if photo_data_list and i < len(photo_data_list) and photo_data_list[i]:
            try:
                pd = photo_data_list[i]
                if isinstance(pd, str):
                    img_bytes = base64.b64decode(pd)
                else:
                    img_bytes = pd
                photo = Image.open(BytesIO(img_bytes)).convert("RGB")
                # Crop to fill column
                ph_ratio = photo.width / photo.height
                col_ratio = col_w / strip_height
                if ph_ratio > col_ratio:
                    new_w = int(photo.height * col_ratio)
                    photo = photo.crop(((photo.width - new_w) // 2, 0,
                                        (photo.width + new_w) // 2, photo.height))
                else:
                    new_h = int(photo.width / col_ratio)
                    photo = photo.crop((0, (photo.height - new_h) // 2,
                                        photo.width, (photo.height + new_h) // 2))
                photo = photo.resize((col_w, strip_height), Image.LANCZOS)
                img.paste(photo, (x_start, strip_top))
            except Exception as e:
                print(f"Photo {i} error: {e}")
                # Placeholder
                draw.rectangle([x_start, strip_top, x_start + col_w, strip_bottom],
                                fill=(210, 205, 198))
        else:
            # Placeholder with subtle gradient
            for py in range(strip_height):
                factor = py / strip_height
                r = int(225 - factor * 15)
                g = int(220 - factor * 15)
                b = int(212 - factor * 15)
                draw.line([(x_start, strip_top + py), (x_start + col_w, strip_top + py)],
                          fill=(r, g, b))

    # Subtle border lines between photos already handled by gap
    # Draw thin lines at strip top
    draw.line([(margin, strip_top - 1), (CANVAS_SIZE[0] - margin, strip_top - 1)],
              fill=ACCENT_COLOR, width=1)

    return img

# ─── SLIDE TYPE 4: QUOTE ────────────────────────────────────────────────────────
def create_quote_slide(quote, author="", slide_number=None):
    """Minimal quote slide: large centered italic quote, author below."""
    img = Image.new("RGB", CANVAS_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)

    if slide_number:
        num_font = load_font("regular", 18)
        draw.text((50, 50), f"0{slide_number}", font=num_font, fill=ACCENT_COLOR)

    draw_brand_logo(draw, position="bottom", color=ACCENT_COLOR)

    # Decorative quotation mark
    font_quote_mark = load_font("regular", 200)
    draw.text((CANVAS_SIZE[0] // 2 - 60, 150), "\u201C", font=font_quote_mark, fill=(225, 218, 208))

    font_quote = load_font("italic", 54)
    font_author = load_font("regular", 26)

    y = 350
    lines = wrap_text(quote, font_quote, 820, draw)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_quote)
        x = (CANVAS_SIZE[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font_quote, fill=TEXT_COLOR)
        y += bbox[3] - bbox[1] + 12

    if author:
        y += 25
        draw_accent_line(draw, y, width=60)
        y += 25
        bbox = draw.textbbox((0, 0), author, font=font_author)
        x = (CANVAS_SIZE[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), author, font=font_author, fill=SUBTITLE_COLOR)

    return img

# ─── MAIN CAROUSEL GENERATOR ─────────────────────────────────────────────────────
def generate_carousel(slides_data):
    """
    Generate all carousel slides and return as list of base64-encoded PNGs.

    slides_data format:
    [
      {
        "type": "cover",        # cover | text | photo | quote
        "title": "...",
        "subtitle": "...",      # optional
        "body": "...",          # optional
        "image": "base64...",   # optional, for cover/photo
        "photos": ["b64", ...], # optional, for photo slide (3 images)
        "slide_number": 1       # optional
      },
      ...
    ]
    """
    results = []

    for i, slide in enumerate(slides_data):
        slide_type = slide.get("type", "text")
        title     = slide.get("title", "")
        subtitle  = slide.get("subtitle", "")
        body      = slide.get("body", "")
        slide_num = slide.get("slide_number", i + 1)

        if slide_type == "cover":
            img = create_cover_slide(
                title=title,
                subtitle=subtitle,
                image_data=slide.get("image")
            )
        elif slide_type == "photo":
            img = create_photo_slide(
                title=title,
                body=body,
                subtitle=subtitle,
                photo_data_list=slide.get("photos"),
                slide_number=slide_num
            )
        elif slide_type == "quote":
            img = create_quote_slide(
                quote=title,
                author=slide.get("author", ""),
                slide_number=slide_num
            )
        else:  # "text" (default)
            img = create_text_slide(
                title=title,
                body=body,
                subtitle=subtitle,
                slide_number=slide_num
            )

        # Convert to base64 PNG
        buffer = BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        results.append({
            "slide_number": slide_num,
            "type": slide_type,
            "image_base64": b64,
            "format": "png"
        })

    return results

# ─── FLASK API ────────────────────────────────────────────────────────────────────
# In-memory store for generated images (served as public URLs for Instagram)
import uuid
import time
_image_store = {}  # {session_id: {slide_num: png_bytes, "created": timestamp}}

def cleanup_old_sessions():
    """Remove sessions older than 30 minutes."""
    cutoff = time.time() - 1800
    old = [k for k, v in _image_store.items() if v.get("created", 0) < cutoff]
    for k in old:
        del _image_store[k]

def create_app():
    try:
        from flask import Flask, request, jsonify, send_file, Response
        app = Flask(__name__)

        @app.route("/health", methods=["GET"])
        def health():
            return jsonify({"status": "ok", "brand": "A.T.O.P.I.C"})

        @app.route("/slides/<session_id>/<int:slide_num>.png", methods=["GET"])
        def serve_slide(session_id, slide_num):
            """Serve a generated slide image by session and slide number."""
            session = _image_store.get(session_id)
            if not session:
                return "Session not found", 404
            img_bytes = session.get(slide_num)
            if not img_bytes:
                return "Slide not found", 404
            return Response(img_bytes, mimetype="image/png",
                            headers={"Cache-Control": "no-cache"})

        @app.route("/generate", methods=["POST"])
        def generate():
            """Generate slides and return public URLs + base64."""
            try:
                cleanup_old_sessions()
                data = request.get_json()
                slides_data = data.get("slides", [])
                if not slides_data:
                    return jsonify({"error": "No slides provided"}), 400

                session_id = str(uuid.uuid4())
                results = generate_carousel(slides_data)

                # Store images for URL serving
                _image_store[session_id] = {"created": time.time()}
                for r in results:
                    img_bytes = base64.b64decode(r["image_base64"])
                    _image_store[session_id][r["slide_number"]] = img_bytes

                # Add public URL to each result
                base_url = request.host_url.rstrip("/")
                for r in results:
                    r["url"] = f"{base_url}/slides/{session_id}/{r['slide_number']}.png"

                return jsonify({"slides": results, "count": len(results),
                                "session_id": session_id})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/generate-from-text", methods=["POST"])
        def generate_from_text():
            """
            Main n8n endpoint.
            Input: { "topic": "...", "slides": [{number, title, body}, ...] }
            Output: { "slides": [{slide_number, url, type}, ...], "urls": [...] }
            """
            try:
                cleanup_old_sessions()
                data = request.get_json()
                topic      = data.get("topic", "Атопический дерматит")
                subtitle   = data.get("subtitle", "Здоровье кожи")
                gpt_slides = data.get("slides", [])   # from GPT-4 output

                slides = []
                # Slide 1: Cover
                slides.append({
                    "type": "cover",
                    "title": topic,
                    "subtitle": subtitle,
                    "slide_number": 1
                })
                # Slides 2–N: Text slides from GPT
                for j, s in enumerate(gpt_slides, start=1):
                    slide_type = "text"
                    # Make one of the middle slides a photo slide
                    if j == 3 and len(gpt_slides) >= 4:
                        slide_type = "photo"
                    slides.append({
                        "type": slide_type,
                        "title": s.get("title", ""),
                        "body":  s.get("body", ""),
                        "subtitle": subtitle,
                        "slide_number": j + 1
                    })

                session_id = str(uuid.uuid4())
                results = generate_carousel(slides)

                # Store for URL serving
                _image_store[session_id] = {"created": time.time()}
                for r in results:
                    img_bytes = base64.b64decode(r["image_base64"])
                    _image_store[session_id][r["slide_number"]] = img_bytes

                base_url = request.host_url.rstrip("/")
                urls = []
                for r in results:
                    url = f"{base_url}/slides/{session_id}/{r['slide_number']}.png"
                    r["url"] = url
                    urls.append(url)
                    del r["image_base64"]  # don't send large base64 back

                return jsonify({
                    "slides": results,
                    "urls": urls,
                    "count": len(results),
                    "session_id": session_id
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        return app
    except ImportError:
        return None

# ─── COMMAND LINE ─────────────────────────────────────────────────────────────────
# ─── WSGI ENTRY POINT (for gunicorn on Render.com) ──────────────────────────────
app = create_app()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        app = create_app()
        if app:
            port = int(os.environ.get("PORT", 5000))
            print(f"Starting Atopic slide API on port {port}")
            app.run(host="0.0.0.0", port=port)
        else:
            print("Flask not available. Install with: pip install flask")

    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # Generate test slides
        print("Generating test carousel slides...")
        test_slides = [
            {
                "type": "cover",
                "title": "Атопический дерматит",
                "subtitle": "5 фактов о коже",
                "slide_number": 1
            },
            {
                "type": "text",
                "title": "Что такое атопия?",
                "body": "Генетически обусловленная склонность к чрезмерным иммунным реакциям на контакт с аллергенами",
                "subtitle": "Разбираемся вместе",
                "slide_number": 2
            },
            {
                "type": "text",
                "title": "Триггеры обострений",
                "body": "Синтетические ткани, бытовая химия, стресс, смена климата и питание",
                "subtitle": "Будьте внимательны",
                "slide_number": 3
            },
            {
                "type": "photo",
                "title": "Уход в период ремиссии",
                "body": "Ежедневное увлажнение — основа базового ухода при атопической коже",
                "subtitle": "Советы A.T.O.P.I.C",
                "slide_number": 4
            },
            {
                "type": "quote",
                "title": "Здоровая кожа — это не результат случайности, а итог ежедневного осознанного ухода",
                "slide_number": 5
            },
            {
                "type": "text",
                "title": "Запишитесь на консультацию",
                "body": "Индивидуальный подход к каждому — напишите нам в Direct",
                "subtitle": "A.T.O.P.I.C",
                "slide_number": 6
            }
        ]

        output_dir = "/sessions/admiring-happy-mayer/test_slides"
        os.makedirs(output_dir, exist_ok=True)

        results = generate_carousel(test_slides)
        for r in results:
            filename = f"{output_dir}/slide_{r['slide_number']}_{r['type']}.png"
            with open(filename, "wb") as f:
                f.write(base64.b64decode(r["image_base64"]))
            print(f"  Saved: slide_{r['slide_number']}_{r['type']}.png")

        print(f"\nDone! {len(results)} slides saved to {output_dir}/")

    else:
        # Read JSON from stdin (for n8n Execute Command node)
        try:
            input_data = json.loads(sys.stdin.read())
            results = generate_carousel(input_data.get("slides", []))
            print(json.dumps({"slides": results, "count": len(results)}))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
