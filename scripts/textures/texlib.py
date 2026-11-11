"""
Shared numpy helpers for the texture pipeline (no Pillow/OpenCV needed).

All images are float32 arrays in [0, 1], shape (H, W, 3), row 0 = top.
Everything that filters uses FFTs on the full image, so it wraps around the
edges: a tileable input stays tileable and generated noise is tileable by design.
"""
import struct
import numpy as np

# ----------------------------------------------------------------- BMP I/O ---

def read_bmp(path):
    data = open(path, "rb").read()
    if data[:2] != b"BM":
        raise ValueError(f"{path}: not a BMP")
    off = struct.unpack_from("<I", data, 10)[0]
    w, h = struct.unpack_from("<ii", data, 18)
    bpp = struct.unpack_from("<H", data, 28)[0]
    if bpp != 24:
        raise ValueError(f"{path}: expected 24-bit BMP, got {bpp}")
    top_down = h < 0
    h = abs(h)
    stride = (w * 3 + 3) & ~3
    raw = np.frombuffer(data, np.uint8, count=stride * h, offset=off).reshape(h, stride)[:, : w * 3]
    img = raw.reshape(h, w, 3)[:, :, ::-1]  # BGR -> RGB
    if not top_down:
        img = img[::-1]
    return img.astype(np.float32) / 255.0


def write_bmp(path, img):
    img = np.clip(img, 0.0, 1.0)
    h, w, _ = img.shape
    u8 = (img * 255.0 + 0.5).astype(np.uint8)[::-1, :, ::-1]  # bottom-up, BGR
    stride = (w * 3 + 3) & ~3
    pad = stride - w * 3
    rows = np.zeros((h, stride), np.uint8)
    rows[:, : w * 3] = u8.reshape(h, w * 3)
    pixels = rows.tobytes()
    header = struct.pack("<2sIHHI", b"BM", 54 + len(pixels), 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(pixels), 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(header + info + pixels)
    _ = pad

# ------------------------------------------------------------ colour space ---

def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(c, 0.0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i: i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def luminance(img):
    return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722

# ------------------------------------------------------- periodic filtering ---

def _gauss_kernel_fft(shape, sigma_px, sigma_y_px=None):
    h, w = shape
    sy = sigma_px if sigma_y_px is None else sigma_y_px
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    return np.exp(-2.0 * (np.pi ** 2) * ((fx * sigma_px) ** 2 + (fy * sy) ** 2))


def blur(img, sigma_px, sigma_y_px=None):
    """Wrap-around Gaussian blur. Works on (H,W) or (H,W,C)."""
    k = _gauss_kernel_fft(img.shape[:2], sigma_px, sigma_y_px)
    if img.ndim == 2:
        return np.real(np.fft.ifft2(np.fft.fft2(img) * k)).astype(np.float32)
    return np.stack([blur(img[..., c], sigma_px, sigma_y_px) for c in range(img.shape[2])], -1)


def dominant_period(profile, kmin=3, kmax=80):
    """Number of repeats across a 1-D wrap-around profile (e.g. brick courses per tile)."""
    p = profile - profile.mean()
    spec = np.abs(np.fft.rfft(p)) ** 2
    kmax = min(kmax, len(spec) - 1)
    k = kmin + int(np.argmax(spec[kmin: kmax + 1]))
    return k, float(spec[k] / (spec[kmin: kmax + 1].sum() + 1e-9))

# ------------------------------------------------------ resample / seams ---

def resize_wrap(img, out_h, out_w):
    """Bilinear resample with wrap-around edges (keeps tileable images tileable).
    Pre-blurs when shrinking to avoid aliasing."""
    h, w = img.shape[:2]
    sy, sx = h / out_h, w / out_w
    if sy > 1 or sx > 1:
        img = blur(img, max(0.0, (sx - 1) * 0.5), max(0.0, (sy - 1) * 0.5))
    ys = (np.arange(out_h) + 0.5) * sy - 0.5
    xs = (np.arange(out_w) + 0.5) * sx - 0.5
    y0 = np.floor(ys).astype(int); fy = (ys - y0)[:, None, None]
    x0 = np.floor(xs).astype(int); fx = (xs - x0)[None, :, None]
    y0m, y1m = y0 % h, (y0 + 1) % h
    x0m, x1m = x0 % w, (x0 + 1) % w
    top = img[y0m][:, x0m] * (1 - fx) + img[y0m][:, x1m] * fx
    bot = img[y1m][:, x0m] * (1 - fx) + img[y1m][:, x1m] * fx
    return (top * (1 - fy) + bot * fy).astype(np.float32)


def fix_vertical_seam(img, search=0.15, band=3, match_sigma=0.0, fade=0):
    """Generated images often tile left-right but not top-bottom. Find rows y0 (near the
    top) and y1 (near the bottom) whose neighbourhoods match best, and crop [y0, y1) so
    the wrap lands where the pattern actually continues. Returns (cropped, kept_fraction).

    match_sigma: blur before matching, so irregular fine detail (straw strands) doesn't
                 drown out the course structure we actually need to line up.
    fade:        rows at the bottom of the crop cross-faded into the rows that precede y0
                 in the source, hiding residual fine-detail mismatch at the wrap."""
    h = img.shape[0]
    s = int(h * search)
    probe = (blur(img, match_sigma) if match_sigma else img)[:, ::4]  # every 4th column: 4x faster
    best = (1e9, 0, h)
    for y0 in range(0, s):
        a = probe[y0: y0 + band]
        for y1 in range(h - s, h - band + 1):
            # rows y1.. should look like rows y0.. (the crop's bottom continues into its top)
            dcost = np.abs(probe[y1: y1 + band] - a).mean()
            if dcost < best[0]:
                best = (dcost, y0, y1)
    _, y0, y1 = best
    out = img[y0:y1].copy()
    if fade:
        pre = img[np.arange(y0 - fade, y0) % h]           # what naturally sits above row y0
        t = (np.arange(fade) + 1) / (fade + 1)
        w = (t * t * (3 - 2 * t))[:, None, None]
        out[-fade:] = out[-fade:] * (1 - w) + pre * w
    return out, (y1 - y0) / h

def blend_vertical_seam(img, band_frac=0.12, shift=None):
    """Offset-blend seam removal: near the top/bottom edges, fade to a copy rolled by
    `shift` rows (default half the height). The rolled copy is continuous across the wrap,
    so the result tiles. Choose `shift` as a whole number of courses to avoid ghosting."""
    h = img.shape[0]
    shift = h // 2 if shift is None else shift
    band = max(1, int(h * band_frac))
    y = np.arange(h)
    d = np.minimum(y, h - 1 - y).astype(np.float32)
    t = np.clip(d / band, 0, 1)
    w = (t * t * (3 - 2 * t))[:, None, None]
    return img * w + np.roll(img, shift, axis=0) * (1 - w)

# --------------------------------------------------------- texture shaping ---

def delight(img, sigma_frac=0.12, strength=0.7):
    """Remove low-frequency light/shade blotches the generator painted in.
    Divides luminance by its heavily blurred version (wrapping, so seams stay clean)."""
    lum = luminance(img) + 1e-4
    low = blur(lum, sigma_frac * img.shape[1])
    gain = (low.mean() / low) ** strength
    return img * gain[..., None]


def match_mean(img, target_srgb, chroma=1.0, contrast=1.0):
    """Shift the texture's average colour to target (in linear light), keeping detail.
    chroma scales saturation around the per-pixel luminance; contrast scales
    luminance deviation from the mean."""
    lin = srgb_to_linear(img)
    target_srgb = np.asarray(target_srgb, np.float32)
    # Scale in linear light, but aim at the average of the *sRGB* image (what the eye and
    # the palette hexes describe). A few fixed-point iterations converge closely.
    for _ in range(4):
        cur = linear_to_srgb(np.clip(lin, 0, 1)).reshape(-1, 3).mean(0)
        lin = lin * (srgb_to_linear(target_srgb) / (srgb_to_linear(cur) + 1e-6))
    if contrast != 1.0:
        l = luminance(lin)[..., None]
        lm = l.mean()
        lin = lin * ((lm + (l - lm) * contrast) / (l + 1e-6))
    if chroma != 1.0:
        l = luminance(lin)[..., None]
        lin = l + (lin - l) * chroma
    return np.clip(linear_to_srgb(lin), 0, 1).astype(np.float32)


def lift_shadows(img, floor=0.10, amount=0.5):
    """Soften hard black ink outlines: pulls very dark values toward `floor`."""
    lum = luminance(img)[..., None]
    t = np.clip((floor - lum) / floor, 0, 1) * amount
    target = img * 0 + floor
    tinted = img + (target - lum) * t * (img / (lum + 1e-4))
    return np.clip(tinted, 0, 1)


def height_from_albedo(img, detail_sigma=1.0, broad_sigma_frac=0.05, invert=False):
    """Approximate height: brighter = raised (bricks over mortar, stones over gaps).
    Band-passed so broad colour changes don't become slopes."""
    h = luminance(img)
    if invert:
        h = 1.0 - h
    h = blur(h, detail_sigma) - blur(h, broad_sigma_frac * img.shape[1])
    return (h - h.min()) / (h.max() - h.min() + 1e-6)


def normal_from_height(height, strength=4.0):
    """Tangent-space normal map, OpenGL convention (+Y up, as glTF/three.js expect)."""
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    # Image row 0 is the top, so "up" in texture space is -row: flip dy for +Y up.
    n = np.stack([-dx * strength, dy * strength, np.ones_like(height)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return (n * 0.5 + 0.5).astype(np.float32)

# --------------------------------------------------------- tileable noise ---

def noise(shape, scale_px, rng, aniso=1.0, octaves=1, persistence=0.5):
    """Tileable fractal noise in [0,1]. scale_px ~ feature size; aniso > 1 stretches along X."""
    h, w = shape
    out = np.zeros(shape, np.float32)
    amp, total, s = 1.0, 0.0, scale_px
    for _ in range(octaves):
        white = rng.standard_normal(shape).astype(np.float32)
        n = blur(white, s * aniso, s)
        n = (n - n.mean()) / (n.std() + 1e-9)
        out += n * amp
        total += amp
        amp *= persistence
        s *= 0.5
    out /= total
    return np.clip(out * 0.25 + 0.5, 0, 1)


def wrap_voronoi(shape, points):
    """Distance to nearest and second-nearest point with wrap-around (for cobbles/stones).
    points: (N,2) array of (y, x) in pixels. Returns (d1, d2, index_of_nearest)."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d1 = np.full(shape, 1e9, np.float32)
    d2 = np.full(shape, 1e9, np.float32)
    idx = np.zeros(shape, np.int32)
    for i, (py, px) in enumerate(points):
        dy = np.abs(yy - py); dy = np.minimum(dy, h - dy)
        dx = np.abs(xx - px); dx = np.minimum(dx, w - dx)
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        idx = np.where(closer, i, idx)
        d1 = np.where(closer, d, d1)
    return d1, d2, idx


def poisson_points(shape, min_dist, rng, tries=6000):
    """Simple dart-throwing blue-noise points with wrap-around spacing."""
    h, w = shape
    pts = []
    for _ in range(tries):
        p = np.array([rng.uniform(0, h), rng.uniform(0, w)])
        ok = True
        for q in pts:
            dy = abs(p[0] - q[0]); dy = min(dy, h - dy)
            dx = abs(p[1] - q[1]); dx = min(dx, w - dx)
            if dx * dx + dy * dy < min_dist * min_dist:
                ok = False
                break
        if ok:
            pts.append(p)
    return np.array(pts, np.float32)
