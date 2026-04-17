"""
Generates icon-192.png and icon-512.png from icon.svg for PWA/iOS/Android.
iOS Safari and Android Chrome do not support SVG as home-screen icons —
they fall back to showing the first letter of the app name ("L").

Tries cairosvg first (best quality), falls back to pure-Python PNG writer.
"""
import os, sys, struct, zlib, math

STATIC   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
SVG_PATH = os.path.join(STATIC, "icon.svg")
SIZES    = [192, 512]


def _try_cairosvg():
    import cairosvg
    for size in SIZES:
        out = os.path.join(STATIC, f"icon-{size}.png")
        cairosvg.svg2png(url=SVG_PATH, write_to=out,
                         output_width=size, output_height=size)
        print(f"  [cairosvg] icon-{size}.png")
    return True


def _make_png(size):
    """Pure-Python RGBA PNG — no third-party deps."""
    W = H = size
    s = size / 512.0

    # Use a flat bytearray: index = (y*W + x)*4
    buf = bytearray(W * H * 4)

    def _set(x, y, r, g, b, a=255):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 4
            sa = a / 255.0; da = buf[i+3] / 255.0
            oa = sa + da * (1.0 - sa)
            if oa > 0:
                buf[i]   = int((r*sa + buf[i]  *da*(1-sa))/oa)
                buf[i+1] = int((g*sa + buf[i+1]*da*(1-sa))/oa)
                buf[i+2] = int((b*sa + buf[i+2]*da*(1-sa))/oa)
                buf[i+3] = int(oa * 255)

    def disk(cx, cy, r, R, G, B, A=255):
        r2 = r*r
        x0 = max(0, int(cx-r)-1); x1 = min(W-1, int(cx+r)+1)
        y0 = max(0, int(cy-r)-1); y1 = min(H-1, int(cy+r)+1)
        for y in range(y0, y1+1):
            dy = y - cy
            for x in range(x0, x1+1):
                if (x-cx)**2 + dy*dy <= r2:
                    _set(x, y, R, G, B, A)

    def arc(cx, cy, radius, t0, t1, thick, R, G, B, steps=None):
        if steps is None:
            steps = max(200, int(radius * abs(t1-t0) * 4))
        half = thick / 2.0
        for i in range(steps+1):
            t  = t0 + (t1-t0)*i/steps
            disk(cx + radius*math.cos(t), cy + radius*math.sin(t), half, R, G, B)

    def rrect(x0, y0, x1, y1, rx, R, G, B, A=255):
        """Rounded rectangle — fast scanline."""
        rx2 = rx*rx
        for y in range(int(y0), int(y1)+1):
            # Determine x span for this scanline
            lx = int(x0); rx_ = int(x1)
            # Left corner zones
            if y < y0+rx:
                dy = y - (y0+rx)
                dx = math.sqrt(max(0, rx2 - dy*dy))
                lx = int(x0+rx - dx)
            elif y > y1-rx:
                dy = y - (y1-rx)
                dx = math.sqrt(max(0, rx2 - dy*dy))
                lx = int(x0+rx - dx)
            # Right corner zones
            if y < y0+rx:
                dy = y - (y0+rx)
                dx = math.sqrt(max(0, rx2 - dy*dy))
                rx_ = int(x1-rx + dx)
            elif y > y1-rx:
                dy = y - (y1-rx)
                dx = math.sqrt(max(0, rx2 - dy*dy))
                rx_ = int(x1-rx + dx)
            for x in range(max(0,lx), min(W-1,rx_)+1):
                _set(x, y, R, G, B, A)

    def triangle(pts, R, G, B, A=255):
        min_y = max(0, int(min(p[1] for p in pts)))
        max_y = min(H-1, int(max(p[1] for p in pts)))
        for y in range(min_y, max_y+1):
            xs = []
            for i in range(3):
                ax,ay = pts[i]; bx2,by2 = pts[(i+1)%3]
                if (ay <= y < by2) or (by2 <= y < ay):
                    if ay != by2:
                        xs.append(ax + (y-ay)*(bx2-ax)/(by2-ay))
            if len(xs) >= 2:
                for x in range(max(0,int(min(xs))), min(W-1,int(max(xs)))+1):
                    _set(x, y, R, G, B, A)

    # ── Background ────────────────────────────────────────────────────────────
    rrect(0, 0, W-1, H-1, 110*s, 0x12, 0x18, 0x20)

    # ── Bubble body ───────────────────────────────────────────────────────────
    bx0,by0 = 88*s, 96*s;  bx1,by1 = 424*s, 377*s;  brx = 40*s
    rrect(bx0, by0, bx1, by1, brx, 0x0d, 0x2a, 0x1f)

    # ── Bubble tail ───────────────────────────────────────────────────────────
    triangle([(148*s,416*s),(164*s,354*s),(220*s,374*s)], 0x0d, 0x2a, 0x1f)

    # ── Neon outline ──────────────────────────────────────────────────────────
    NR,NG,NB = 0x00, 0xFF, 0x88
    ow = max(2, int(7*s))
    for t in range(ow):
        for x in range(int(bx0+brx), int(bx1-brx)+1):
            _set(x, int(by0)+t, NR,NG,NB)
            _set(x, int(by1)-t, NR,NG,NB)
        for y in range(int(by0+brx), int(by1-brx)+1):
            _set(int(bx0)+t, y, NR,NG,NB)
            _set(int(bx1)-t, y, NR,NG,NB)
    for (ccx,ccy,a0,a1) in [
        (bx0+brx, by0+brx, math.pi,       1.5*math.pi),
        (bx1-brx, by0+brx, 1.5*math.pi,   2.0*math.pi),
        (bx0+brx, by1-brx, 0.5*math.pi,   math.pi),
        (bx1-brx, by1-brx, 0.0,            0.5*math.pi),
    ]:
        arc(ccx, ccy, brx, a0, a1, ow, NR,NG,NB)

    # ── WiFi arcs ─────────────────────────────────────────────────────────────
    acx = 256*s;  acy = 288*s;  aw = max(2, int(14*s))
    a0 = math.radians(210);  a1 = math.radians(330)
    for rd in [115, 80, 45]:
        arc(acx, acy, rd*s*0.6, a0, a1, aw, NR,NG,NB)

    # ── Centre dot ────────────────────────────────────────────────────────────
    disk(acx, acy, 14*s, NR,NG,NB)

    # ── Encode PNG ────────────────────────────────────────────────────────────
    def chunk(tag, data):
        crc = zlib.crc32(tag+data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    rows = bytearray()
    for y in range(H):
        rows += b'\x00'
        rows += buf[y*W*4:(y+1)*W*4]

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 6))
            + chunk(b"IEND", b""))


def _builtin_fallback():
    for size in SIZES:
        out  = os.path.join(STATIC, f"icon-{size}.png")
        data = _make_png(size)
        with open(out, "wb") as f:
            f.write(data)
        print(f"  [built-in] icon-{size}.png  ({len(data):,} bytes)")
    return True


if __name__ == "__main__":
    print("Generating PNG icons for PWA/iOS/Android...")
    ok = False
    try:
        ok = _try_cairosvg()
    except Exception:
        pass
    if not ok:
        ok = _builtin_fallback()
    print("  Done — icon-192.png and icon-512.png are ready." if ok else
          "  WARNING: icon generation failed.")
    sys.exit(0 if ok else 1)
