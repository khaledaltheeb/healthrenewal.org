#!/usr/bin/env python3
"""Render original 1280x720 topic-led illustrations for Quick Information.

The cards intentionally avoid title-card layouts and embedded article headlines.
They use simple original vector-like scenes, profile-specific symbols, strong
focal points, safe contrast and deterministic variation. This makes the image
useful on its own in Discover, social previews and related-content cards.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from PIL import Image, ImageDraw

from generate_quick_info import CARD_DIR, TOPICS, profile_key

W, H = 1280, 720

PALETTES = {
    "depression": ((21, 55, 78), (94, 151, 166), (248, 205, 92)),
    "sadness": ((48, 72, 103), (117, 164, 184), (238, 204, 128)),
    "anxiety": ((45, 50, 92), (122, 102, 171), (109, 219, 199)),
    "stress": ((49, 75, 83), (120, 172, 165), (242, 175, 112)),
    "burnout": ((76, 49, 70), (171, 105, 124), (248, 195, 119)),
    "fatigue": ((48, 68, 77), (126, 159, 159), (231, 199, 132)),
    "sleep": ((19, 40, 84), (72, 91, 151), (245, 221, 137)),
    "attention": ((18, 82, 91), (75, 176, 168), (250, 198, 83)),
    "adhd": ((17, 91, 95), (78, 193, 173), (244, 179, 80)),
    "social": ((59, 56, 105), (151, 119, 174), (242, 194, 135)),
    "relationship": ((91, 43, 75), (207, 107, 145), (244, 197, 160)),
    "attachment": ((88, 45, 83), (190, 101, 156), (113, 212, 198)),
    "breakup": ((74, 49, 91), (157, 105, 157), (245, 177, 137)),
    "boundaries": ((26, 85, 82), (82, 174, 153), (242, 194, 118)),
    "loneliness": ((43, 63, 91), (101, 145, 169), (239, 195, 118)),
    "digital": ((28, 58, 94), (64, 153, 174), (246, 190, 92)),
    "addiction": ((60, 62, 87), (109, 139, 153), (238, 174, 92)),
    "panic": ((58, 48, 91), (139, 108, 171), (107, 217, 197)),
    "ocd": ((35, 61, 86), (95, 150, 167), (238, 183, 103)),
    "bipolar": ((54, 47, 92), (151, 107, 175), (241, 197, 101)),
    "procrastination": ((34, 75, 80), (112, 165, 153), (244, 184, 92)),
    "eating": ((91, 53, 65), (196, 119, 119), (246, 201, 128)),
    "anger": ((103, 47, 54), (213, 100, 83), (248, 194, 91)),
    "child": ((36, 86, 80), (94, 185, 157), (246, 196, 94)),
    "teen": ((42, 66, 103), (100, 150, 184), (244, 184, 116)),
    "sensory": ((59, 52, 103), (151, 111, 180), (110, 218, 199)),
    "caregiver": ((39, 81, 76), (105, 174, 148), (240, 190, 108)),
}


def seed_for(slug: str) -> int:
    return int(hashlib.sha256(slug.encode("utf-8")).hexdigest()[:16], 16)


def lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def background(draw: ImageDraw.ImageDraw, palette, seed: int) -> None:
    dark, mid, accent = palette
    for y in range(H):
        t = y / (H - 1)
        c = tuple(lerp(dark[i], mid[i], t) for i in range(3))
        draw.line((0, y, W, y), fill=c)
    # Organic light fields, varied deterministically.
    for i in range(7):
        angle = ((seed >> (i * 5)) & 255) / 255 * math.tau
        radius = 140 + ((seed >> (i * 7)) & 127)
        cx = int(W * .5 + math.cos(angle) * (320 + i * 18))
        cy = int(H * .5 + math.sin(angle) * (190 + i * 10))
        alpha = 15 + i * 3
        draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=(*accent, alpha))
    draw.rounded_rectangle((55, 55, W-55, H-55), radius=46, outline=(255,255,255,45), width=3)


def person(draw, x, y, scale=1.0, color=(248,248,244,235), facing=1):
    r = int(44 * scale)
    draw.ellipse((x-r, y-r, x+r, y+r), fill=color)
    shoulder_w = int(115 * scale)
    body_h = int(180 * scale)
    draw.rounded_rectangle((x-shoulder_w, y+r+18, x+shoulder_w, y+r+body_h), radius=int(60*scale), fill=color)
    # face direction as a tiny nose cue
    draw.ellipse((x + facing*int(23*scale), y-int(6*scale), x + facing*int(31*scale), y+int(2*scale)), fill=(30,55,65,90))


def heart(draw, cx, cy, size, color):
    r = size // 4
    draw.ellipse((cx-size//2, cy-size//3, cx, cy+size//6), fill=color)
    draw.ellipse((cx, cy-size//3, cx+size//2, cy+size//6), fill=color)
    draw.polygon([(cx-size//2, cy), (cx+size//2, cy), (cx, cy+size//2)], fill=color)


def moon_scene(draw, palette, seed):
    _, _, accent = palette
    draw.ellipse((770, 115, 1080, 425), fill=(*accent, 245))
    draw.ellipse((850, 80, 1110, 350), fill=(42,65,110,255))
    draw.rounded_rectangle((170, 420, 860, 585), radius=55, fill=(244,247,243,225))
    draw.rounded_rectangle((220, 350, 480, 470), radius=50, fill=(221,231,226,245))
    for i in range(9):
        x = 130 + ((seed >> (i*4)) & 1023) % 1000
        y = 90 + ((seed >> (i*6)) & 511) % 250
        draw.ellipse((x, y, x+7+i%3*2, y+7+i%3*2), fill=(255,248,207,190))


def relationship_scene(draw, palette, seed, separated=False, boundary=False):
    _, _, accent = palette
    person(draw, 390, 260, .95, (250,244,239,235), 1)
    person(draw, 890, 260, .95, (238,248,246,235), -1)
    if boundary:
        draw.rounded_rectangle((617, 125, 663, 595), radius=22, fill=(*accent, 220))
    elif separated:
        draw.line((520, 420, 760, 300), fill=(255,255,255,190), width=14)
        draw.line((520, 300, 760, 420), fill=(*accent, 230), width=14)
    else:
        heart(draw, 640, 315, 135, (*accent, 240))
        draw.arc((470, 250, 810, 560), 205, 335, fill=(255,255,255,150), width=10)


def mind_scene(draw, palette, seed, tangled=False, target=False):
    _, _, accent = palette
    person(draw, 360, 270, 1.05, (247,247,240,235), 1)
    cx, cy = 825, 330
    draw.ellipse((cx-190, cy-190, cx+190, cy+190), fill=(245,250,246,210), outline=(*accent,220), width=10)
    if target:
        for r in (145, 100, 55):
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=(*accent, 170 + (145-r)//2), width=12)
        draw.ellipse((cx-18, cy-18, cx+18, cy+18), fill=(*accent,255))
    elif tangled:
        points=[]
        for i in range(90):
            a=i*.42
            r=15+i*1.55 + 18*math.sin(i*.77 + (seed%17))
            points.append((cx+math.cos(a)*r, cy+math.sin(a)*r))
        draw.line(points, fill=(*accent,235), width=9, joint="curve")
    else:
        for i in range(7):
            a=i*math.tau/7 + (seed%31)/31
            x=cx+math.cos(a)*115; y=cy+math.sin(a)*115
            draw.ellipse((x-18,y-18,x+18,y+18),fill=(*accent,230))
            draw.line((cx,cy,x,y),fill=(*accent,150),width=7)


def digital_scene(draw, palette, seed):
    _, _, accent = palette
    draw.rounded_rectangle((420, 85, 860, 635), radius=65, fill=(237,246,244,235), outline=(255,255,255,180), width=8)
    draw.rounded_rectangle((470, 155, 810, 525), radius=35, fill=(*accent,210))
    for i in range(5):
        y=205+i*62
        draw.rounded_rectangle((515,y,765,y+28),radius=14,fill=(255,255,255,125+i*15))
    draw.ellipse((615,555,665,605),fill=(*accent,230))
    for i in range(4):
        r=45+i*35
        draw.arc((640-r,80-r,640+r,80+r),200,340,fill=(255,255,255,110),width=8)


def family_scene(draw, palette, seed):
    _, _, accent = palette
    person(draw, 420, 265, .95, (250,245,236,235), 1)
    person(draw, 850, 265, .95, (236,249,244,235), -1)
    person(draw, 640, 380, .62, (*accent,235), 1)
    draw.arc((300,180,980,650),200,340,fill=(255,255,255,150),width=13)


def five_scene(draw, palette, seed):
    _, _, accent = palette
    cx, cy = 640, 355
    draw.ellipse((cx-95,cy-95,cx+95,cy+95),fill=(246,249,244,225),outline=(*accent,230),width=9)
    for i in range(5):
        a=-math.pi/2+i*math.tau/5 + (seed%13)*.01
        x=cx+math.cos(a)*245; y=cy+math.sin(a)*245
        draw.line((cx,cy,x,y),fill=(255,255,255,145),width=10)
        draw.ellipse((x-58,y-58,x+58,y+58),fill=(*accent,225),outline=(255,255,255,170),width=7)


def addiction_scene(draw, palette, seed):
    _, _, accent = palette
    cx, cy=640,350
    for i,(start,end) in enumerate(((20,145),(155,280),(290,415))):
        box=(cx-230+i*30,cy-230+i*20,cx+230-i*30,cy+230-i*20)
        draw.arc(box,start,end,fill=(*accent,220-i*20),width=24)
    person(draw,640,285,.75,(247,247,240,235),1)
    draw.line((400,570,880,570),fill=(255,255,255,160),width=16)
    draw.ellipse((850,535,920,605),fill=(*accent,240))


def eating_scene(draw,palette,seed):
    _,_,accent=palette
    draw.ellipse((310,170,970,650),fill=(243,246,238,230),outline=(255,255,255,170),width=9)
    draw.ellipse((425,260,855,590),fill=(*accent,185))
    draw.arc((475,305,805,535),15,165,fill=(255,255,255,210),width=22)
    draw.line((260,140,260,610),fill=(255,255,255,210),width=18)
    draw.line((1020,140,1020,610),fill=(255,255,255,210),width=18)


def sensory_scene(draw,palette,seed):
    _,_,accent=palette
    person(draw,640,320,1.0,(247,247,240,235),1)
    for i in range(12):
        a=i*math.tau/12+(seed%29)*.01
        r1=220; r2=315+(i%3)*20
        x1=640+math.cos(a)*r1; y1=350+math.sin(a)*r1
        x2=640+math.cos(a)*r2; y2=350+math.sin(a)*r2
        draw.line((x1,y1,x2,y2),fill=(*accent,120+i*8),width=8+i%3*3)


def render(slug: str, title: str, category: str) -> None:
    key = profile_key(title)
    palette = PALETTES.get(key, PALETTES["stress"])
    seed = seed_for(slug)
    im = Image.new("RGBA", (W,H), palette[0]+(255,))
    draw = ImageDraw.Draw(im, "RGBA")
    background(draw,palette,seed)

    if key == "sleep": moon_scene(draw,palette,seed)
    elif key in {"relationship","attachment"}: relationship_scene(draw,palette,seed,boundary="حدود" in title or "سيطرة" in title)
    elif key == "breakup": relationship_scene(draw,palette,seed,separated=True)
    elif key == "boundaries": relationship_scene(draw,palette,seed,boundary=True)
    elif key == "digital": digital_scene(draw,palette,seed)
    elif key in {"child","teen","caregiver"}: family_scene(draw,palette,seed)
    elif key == "sensory": sensory_scene(draw,palette,seed)
    elif key == "addiction": addiction_scene(draw,palette,seed)
    elif key == "eating": eating_scene(draw,palette,seed)
    elif category == "أسباب وعلامات": five_scene(draw,palette,seed)
    elif key in {"attention","adhd"}: mind_scene(draw,palette,seed,target=True)
    elif key in {"anxiety","panic","ocd","procrastination","stress","burnout"}: mind_scene(draw,palette,seed,tangled=True)
    else: mind_scene(draw,palette,seed,tangled=False)

    # Small unobtrusive provenance mark; never a logo-only card.
    draw.ellipse((82,82,128,128),fill=(255,255,255,190))
    draw.ellipse((95,95,115,115),fill=(*palette[2],235))
    CARD_DIR.mkdir(parents=True,exist_ok=True)
    im.convert("RGB").save(CARD_DIR/f"{slug}.jpg","JPEG",quality=90,optimize=True,progressive=True)


def main() -> None:
    for slug,title,_kind,category in TOPICS:
        render(slug,title,category)
    files=list(CARD_DIR.glob("*.jpg"))
    if len(files)!=150:
        raise SystemExit(f"Expected 150 cards, found {len(files)}")
    undersized=[p.name for p in files if p.stat().st_size<30000]
    if undersized:
        raise SystemExit(f"Illustrations unexpectedly small: {undersized[:5]}")
    print({"rendered":len(files),"size":"1280x720","embedded_headlines":0,"renderer":"topic-led-v2"})


if __name__=="__main__":
    main()
