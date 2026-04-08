#!/usr/bin/env python3
"""
raytracer.py — a terminal ASCII ray tracer
zero dependencies · pure stdlib · single file

Renders: spheres, planes, point lights, shadows,
         reflections, ambient/diffuse/specular shading

Now with proper PPM export and consistent gamma correction.

usage:
  python3 raytracer.py                  # default scene
  python3 raytracer.py --width 160      # wider render
  python3 raytracer.py --scene 2        # alternate scene
  python3 raytracer.py --anim           # spinning animation
  python3 raytracer.py --ppm out.ppm    # save as proper image
  python3 raytracer.py --color          # ANSI 24-bit color
  
  (I'm using Python3 in Ubuntu)

Built by PithyCyborg — https://pithycyborg.com
Join my free AI newsletter for more from-scratch coding, systems projects,
and no-BS AI insights: https://pithycyborg.com/newsletter
"""

import math
import sys
import time
import os
import argparse

# ─── math primitives ──────────────────────────────────────────────────────────

class Vec3:
    __slots__ = ("x", "y", "z")

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, o):
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __iadd__(self, o):
        self.x += o.x
        self.y += o.y
        self.z += o.z
        return self

    def __sub__(self, o):
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, t):
        if isinstance(t, Vec3):
            return Vec3(self.x * t.x, self.y * t.y, self.z * t.z)
        return Vec3(self.x * t, self.y * t, self.z * t)

    def __rmul__(self, t):
        return self.__mul__(t)

    def __neg__(self):
        return Vec3(-self.x, -self.y, -self.z)

    def __truediv__(self, t):
        return Vec3(self.x / t, self.y / t, self.z / t)

    def dot(self, o):
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o):
        return Vec3(self.y * o.z - self.z * o.y,
                    self.z * o.x - self.x * o.z,
                    self.x * o.y - self.y * o.x)

    def length(self):
        return math.sqrt(self.dot(self))

    def normalize(self):
        l = self.length()
        return self / l if l > 1e-12 else Vec3()

    def reflect(self, n):
        return self - n * (2 * self.dot(n))

    def clamp(self, lo=0.0, hi=1.0):
        return Vec3(max(lo, min(hi, self.x)),
                    max(lo, min(hi, self.y)),
                    max(lo, min(hi, self.z)))

    def __repr__(self):
        return f"Vec3({self.x:.3f},{self.y:.3f},{self.z:.3f})"


class Ray:
    __slots__ = ("origin", "direction")

    def __init__(self, origin, direction):
        self.origin = origin
        self.direction = direction.normalize()

    def at(self, t):
        return self.origin + self.direction * t


# ─── scene objects ─────────────────────────────────────────────────────────────

class Material:
    def __init__(self, color, ambient=0.1, diffuse=0.8, specular=0.5,
                 shininess=32, reflectivity=0.0):
        self.color = color
        self.ambient = ambient
        self.diffuse = diffuse
        self.specular = specular
        self.shininess = shininess
        self.reflectivity = reflectivity


class HitRecord:
    __slots__ = ("t", "point", "normal", "material")

    def __init__(self, t, point, normal, material):
        self.t = t
        self.point = point
        self.normal = normal
        self.material = material


class Sphere:
    def __init__(self, center, radius, material):
        self.center = center
        self.radius = radius
        self.material = material

    def hit(self, ray, t_min, t_max):
        oc = ray.origin - self.center
        a = ray.direction.dot(ray.direction)
        hb = oc.dot(ray.direction)
        c = oc.dot(oc) - self.radius * self.radius
        disc = hb * hb - a * c
        if disc < 0:
            return None
        sq = math.sqrt(disc)
        for root in ((-hb - sq) / a, (-hb + sq) / a):
            if t_min < root < t_max:
                pt = ray.at(root)
                n = (pt - self.center) / self.radius
                return HitRecord(root, pt, n, self.material)
        return None


class Plane:
    def __init__(self, point, normal, material):
        self.point = point
        self.normal = normal.normalize()
        self.material = material

    def hit(self, ray, t_min, t_max):
        denom = self.normal.dot(ray.direction)
        if abs(denom) < 1e-8:
            return None
        t = (self.point - ray.origin).dot(self.normal) / denom
        if t_min < t < t_max:
            return HitRecord(t, ray.at(t), self.normal, self.material)
        return None


class PointLight:
    def __init__(self, position, color, intensity=1.0):
        self.position = position
        self.color = color
        self.intensity = intensity


# ─── renderer ─────────────────────────────────────────────────────────────────

INF = float("inf")


def nearest_hit(ray, objects, t_min=1e-4, t_max=INF):
    closest = None
    best_t = t_max
    for obj in objects:
        rec = obj.hit(ray, t_min, best_t)
        if rec and rec.t < best_t:
            best_t = rec.t
            closest = rec
    return closest


def shade(ray, objects, lights, hit, depth=0, max_depth=4):
    mat = hit.material
    n = hit.normal
    p = hit.point
    v = (-ray.direction).normalize()

    color = mat.color * mat.ambient

    for light in lights:
        to_light = light.position - p
        dist_light = to_light.length()
        l = to_light.normalize()

        # shadow ray
        shadow_ray = Ray(p, l)
        shadow_hit = nearest_hit(shadow_ray, objects, 1e-4, dist_light - 1e-4)
        if shadow_hit:
            continue

        # diffuse
        diff = max(0.0, n.dot(l))
        color += mat.color * light.color * (mat.diffuse * diff * light.intensity)

        # specular (blinn-phong)
        h = (l + v).normalize()
        spec = max(0.0, n.dot(h)) ** mat.shininess
        color += light.color * (mat.specular * spec * light.intensity)

    # reflection
    if depth < max_depth and mat.reflectivity > 0:
        ref_dir = ray.direction.reflect(n)
        ref_ray = Ray(p, ref_dir)
        ref_col = trace(ref_ray, objects, lights, depth + 1, max_depth)
        color += ref_col * mat.reflectivity

    return color.clamp()


def trace(ray, objects, lights, depth=0, max_depth=4):
    hit = nearest_hit(ray, objects)
    if hit:
        return shade(ray, objects, lights, hit, depth, max_depth)
    # sky gradient
    t = 0.5 * (ray.direction.y + 1.0)
    return Vec3(1, 1, 1) * (1 - t) + Vec3(0.4, 0.6, 1.0) * t


# ─── ASCII palette ─────────────────────────────────────────────────────────────

PALETTE_DENSE = r'$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,"^`\'. '
PALETTE_SIMPLE = r'@#S%?*+;:,. '
PALETTE_BLOCK = '█▓▒░ '


def luminance(c):
    return 0.2126 * c.x + 0.7152 * c.y + 0.0722 * c.z


def to_ascii(brightness, palette=PALETTE_SIMPLE):
    idx = int(brightness * (len(palette) - 1))
    idx = max(0, min(len(palette) - 1, idx))
    return palette[len(palette) - 1 - idx]


# ─── camera ───────────────────────────────────────────────────────────────────

class Camera:
    def __init__(self, pos, look_at, up, fov_deg, aspect):
        self.pos = pos
        fov_rad = math.radians(fov_deg)
        h = math.tan(fov_rad / 2)
        w_half = h * aspect
        z = (pos - look_at).normalize()
        x = up.cross(z).normalize()
        y = z.cross(x)
        self.lower_left = pos - x * w_half - y * h - z
        self.horiz = x * (2 * w_half)
        self.vert = y * (2 * h)

    def get_ray(self, u, v):
        target = self.lower_left + self.horiz * u + self.vert * v
        return Ray(self.pos, target - self.pos)


# ─── scenes ───────────────────────────────────────────────────────────────────

def scene_classic(t=0.0):
    cos_t = math.cos(t)
    sin_t = math.sin(t)

    mat_red = Material(Vec3(0.9, 0.2, 0.2), reflectivity=0.1)
    mat_chrome = Material(Vec3(0.9, 0.9, 0.9), ambient=0.05, diffuse=0.3,
                          specular=1.0, shininess=128, reflectivity=0.7)
    mat_blue = Material(Vec3(0.2, 0.4, 0.9), reflectivity=0.15, shininess=64)
    mat_floor = Material(Vec3(0.8, 0.8, 0.8), ambient=0.05, diffuse=0.9,
                         specular=0.1, shininess=4, reflectivity=0.05)
    mat_small = Material(Vec3(0.9, 0.7, 0.1), specular=0.8, shininess=96)

    objects = [
        Plane(Vec3(0, -1, 0), Vec3(0, 1, 0), mat_floor),
        Sphere(Vec3(-1.8 * cos_t, 0.5, -1.8 * sin_t), 1.5, mat_chrome),
        Sphere(Vec3(2.0, 0.5, 1.0), 1.5, mat_red),
        Sphere(Vec3(0, 0.5, 3.0), 1.5, mat_blue),
        Sphere(Vec3(0.5, -0.4, 0.8), 0.6, mat_small),
    ]
    lights = [
        PointLight(Vec3(-4, 6, -3), Vec3(1, 1, 1), 1.0),
        PointLight(Vec3(4, 4, 2), Vec3(0.8, 0.85, 1.0), 0.5),
    ]
    cam = Camera(Vec3(0, 2.5, 8), Vec3(0, 0.3, 0),
                 Vec3(0, 1, 0), fov_deg=55, aspect=2.0)
    return objects, lights, cam


def scene_solar(t=0.0):
    mat_sun = Material(Vec3(1.0, 0.8, 0.1), ambient=0.9, diffuse=0.5,
                       specular=1.0, shininess=200, reflectivity=0.0)
    mat_e = Material(Vec3(0.2, 0.5, 0.9), reflectivity=0.1)
    mat_m = Material(Vec3(0.8, 0.3, 0.2), reflectivity=0.05)
    mat_moon = Material(Vec3(0.75, 0.75, 0.75), reflectivity=0.05)
    mat_ring = Material(Vec3(0.9, 0.8, 0.6), ambient=0.05, diffuse=0.9,
                        specular=0.2, shininess=8)

    e_angle = t
    m_angle = t * 1.88
    moon_a = t * 13.4

    ex = math.cos(e_angle) * 5
    ez = math.sin(e_angle) * 5
    mx = math.cos(m_angle) * 8.5
    mz = math.sin(m_angle) * 8.5

    objects = [
        Plane(Vec3(0, -3, 0), Vec3(0, 1, 0),
              Material(Vec3(0.05, 0.05, 0.1), ambient=0.02, diffuse=0.5,
                       specular=0.0, reflectivity=0.0)),
        Sphere(Vec3(0, 0, 0), 1.6, mat_sun),
        Sphere(Vec3(ex, 0, ez), 0.55, mat_e),
        Sphere(Vec3(ex + math.cos(moon_a) * 1.1, 0.1,
                    ez + math.sin(moon_a) * 1.1), 0.18, mat_moon),
        Sphere(Vec3(mx, 0, mz), 0.42, mat_m),
        Sphere(Vec3(-3.5, 0.5, -6.0), 0.9, mat_ring),
    ]
    lights = [
        PointLight(Vec3(0, 0.2, 0), Vec3(1.0, 0.92, 0.7), 2.0),
        PointLight(Vec3(0, 12, 0), Vec3(0.3, 0.3, 0.5), 0.3),
    ]
    cam = Camera(Vec3(0, 6, 14), Vec3(0, 0, 0),
                 Vec3(0, 1, 0), fov_deg=50, aspect=2.0)
    return objects, lights, cam


def scene_corridor(t=0.0):
    shiny = Material(Vec3(0.85, 0.85, 0.95), ambient=0.03, diffuse=0.2,
                     specular=1.0, shininess=256, reflectivity=0.8)
    warm = Material(Vec3(1.0, 0.4, 0.1), ambient=0.1, diffuse=0.7,
                    specular=0.9, shininess=64, reflectivity=0.4)
    cool = Material(Vec3(0.1, 0.6, 1.0), ambient=0.1, diffuse=0.7,
                    specular=0.9, shininess=64, reflectivity=0.4)
    floor_mat = Material(Vec3(0.6, 0.6, 0.65), ambient=0.05, diffuse=0.6,
                         specular=0.5, shininess=32, reflectivity=0.3)

    offsets = [-4, -2, 0, 2, 4]
    objects = [Plane(Vec3(0, -1.5, 0), Vec3(0, 1, 0), floor_mat)]
    for i, ox in enumerate(offsets):
        obj_t = t + i * 1.2
        y = math.sin(obj_t) * 0.5
        m = warm if i % 2 == 0 else cool
        objects.append(Sphere(Vec3(ox, y, -2.0 - i * 1.5), 0.7, m))
        objects.append(Sphere(Vec3(ox * 0.6, y + 1.2, -3.0 - i), 0.35, shiny))

    lights = [
        PointLight(Vec3(0, 5, 2), Vec3(1, 0.9, 0.8), 1.2),
        PointLight(Vec3(-3, 2, -5), Vec3(0.4, 0.6, 1.0), 0.8),
        PointLight(Vec3(3, 1, -8), Vec3(1.0, 0.4, 0.2), 0.6),
    ]
    cam = Camera(Vec3(0, 1.5, 6), Vec3(0, 0.5, 0),
                 Vec3(0, 1, 0), fov_deg=65, aspect=2.0)
    return objects, lights, cam


SCENES = {1: scene_classic, 2: scene_solar, 3: scene_corridor}
SCENE_NAMES = {1: "classic", 2: "solar system", 3: "reflective corridor"}


# ─── render functions ─────────────────────────────────────────────────────────

def render(width, height, objects, lights, cam,
           palette=PALETTE_SIMPLE, max_depth=4):
    rows = []
    for j in range(height - 1, -1, -1):
        row = []
        for i in range(width):
            u = i / (width - 1)
            v = j / (height - 1)
            ray = cam.get_ray(u, v)
            color = trace(ray, objects, lights, max_depth=max_depth)
            lum = math.sqrt(luminance(color))
            row.append(to_ascii(lum, palette))
        rows.append("".join(row))
    return rows


def render_color(width, height, objects, lights, cam,
                 palette=PALETTE_SIMPLE, max_depth=4):
    rows = []
    for j in range(height - 1, -1, -1):
        row = []
        for i in range(width):
            u = i / (width - 1)
            v = j / (height - 1)
            ray = cam.get_ray(u, v)
            color = trace(ray, objects, lights, max_depth=max_depth)
            color = Vec3(math.sqrt(color.x), math.sqrt(color.y), math.sqrt(color.z))
            lum = luminance(color)
            char = to_ascii(lum, palette)
            r8 = int(color.x * 255)
            g8 = int(color.y * 255)
            b8 = int(color.z * 255)
            row.append(f"\x1b[38;2;{r8};{g8};{b8}m{char}\x1b[0m")
        rows.append("".join(row))
    return rows


def render_pixels(width, height, objects, lights, cam, max_depth=4):
    """Render to a flat list of (r,g,b) tuples, top-to-bottom."""
    pixels = []
    for j in range(height - 1, -1, -1):
        for i in range(width):
            u = i / (width - 1)
            v = j / (height - 1)
            ray = cam.get_ray(u, v)
            color = trace(ray, objects, lights, max_depth=max_depth)
            r = max(0, min(255, int(255 * math.sqrt(color.x))))
            g = max(0, min(255, int(255 * math.sqrt(color.y))))
            b = max(0, min(255, int(255 * math.sqrt(color.z))))
            pixels.append((r, g, b))
    return pixels


def save_ppm(filename, width, height, objects, lights, cam, max_depth=4):
    """Save render as 24-bit binary PPM image."""
    print(f"rendering {width}x{height} PPM...")
    pixels = render_pixels(width, height, objects, lights, cam, max_depth)
    with open(filename, "wb") as f:
        f.write(f"P6\n{width} {height}\n255\n".encode())
        for r, g, b in pixels:
            f.write(bytes([r, g, b]))
    print(f"saved PPM → {filename}")


def save_png(filename, width, height, objects, lights, cam, max_depth=4):
    """Save render as PNG using only stdlib (zlib + struct). No Pillow needed."""
    import zlib, struct

    print(f"rendering {width}x{height} PNG...")
    pixels = render_pixels(width, height, objects, lights, cam, max_depth)

    def png_chunk(tag, data):
        c = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", c)

    # PNG signature
    sig = b"\x89PNG\r\n\x1a\n"

    # IHDR: width, height, bit depth=8, color type=2 (RGB), compress=0, filter=0, interlace=0
    ihdr = png_chunk(b"IHDR",
        struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))

    # IDAT: raw scanlines with filter byte 0 (None) prepended to each row
    raw_rows = []
    for row_start in range(0, width * height, width):
        row_bytes = bytearray([0])  # filter byte
        for r, g, b in pixels[row_start:row_start + width]:
            row_bytes += bytes([r, g, b])
        raw_rows.append(bytes(row_bytes))

    compressed = zlib.compress(b"".join(raw_rows), level=6)
    idat = png_chunk(b"IDAT", compressed)

    iend = png_chunk(b"IEND", b"")

    with open(filename, "wb") as f:
        f.write(sig + ihdr + idat + iend)

    size_kb = os.path.getsize(filename) / 1024
    print(f"saved PNG  → {filename}  ({size_kb:.1f} KB)")


# ─── terminal helpers ─────────────────────────────────────────────────────────

def get_terminal_size(fallback=(80, 24)):
    try:
        s = os.get_terminal_size()
        return s.columns, s.lines
    except OSError:
        return fallback


def clear_screen():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def move_cursor_home():
    sys.stdout.write("\x1b[H")
    sys.stdout.flush()


def hide_cursor():
    sys.stdout.write("\x1b[?25l")
    sys.stdout.flush()


def show_cursor():
    sys.stdout.write("\x1b[?25h")
    sys.stdout.flush()


def print_frame(rows, title=""):
    move_cursor_home()
    if title:
        sys.stdout.write(f"\x1b[1m{title}\x1b[0m\n")
    sys.stdout.write("\n".join(rows) + "\n")
    sys.stdout.flush()


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="ASCII ray tracer — zero deps, pure Python",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
scenes:
  1  classic      three spheres, chrome + matte
  2  solar        mini solar system with orbits
  3  corridor     abstract reflective corridor

examples:
  python raytracer.py
  python raytracer.py --scene 2 --anim
  python raytracer.py --width 160 --color
  python raytracer.py --ppm out.ppm --img-width 800 --img-height 450
  python raytracer.py --png out.png --img-width 1280 --img-height 720
        """
    )
    ap.add_argument("--width",      type=int,   default=0,
                    help="terminal render width in chars")
    ap.add_argument("--height",     type=int,   default=0,
                    help="terminal render height in chars")
    ap.add_argument("--img-width",  type=int,   default=800,
                    help="image output width in pixels (default: 800)")
    ap.add_argument("--img-height", type=int,   default=450,
                    help="image output height in pixels (default: 450)")
    ap.add_argument("--scene",  type=int,   default=1, choices=[1, 2, 3])
    ap.add_argument("--depth",  type=int,   default=4)
    ap.add_argument("--anim",   action="store_true")
    ap.add_argument("--fps",    type=float, default=12.0)
    ap.add_argument("--color",  action="store_true")
    ap.add_argument("--dense",  action="store_true")
    ap.add_argument("--save",   type=str,   default="",
                    help="save ASCII frame to text file")
    ap.add_argument("--ppm",    type=str,   default="",
                    help="save as PPM image (use --img-width/--img-height)")
    ap.add_argument("--png",    type=str,   default="",
                    help="save as PNG image (stdlib zlib, no Pillow needed)")
    args = ap.parse_args()

    palette  = PALETTE_DENSE if args.dense else PALETTE_SIMPLE
    scene_fn = SCENES[args.scene]
    name     = SCENE_NAMES[args.scene]
    objects, lights, cam = scene_fn(0.0)

    # ── image outputs ─────────────────────────────────────────────────────────
    if args.ppm:
        save_ppm(args.ppm, args.img_width, args.img_height,
                 objects, lights, cam, args.depth)
        return

    if args.png:
        save_png(args.png, args.img_width, args.img_height,
                 objects, lights, cam, args.depth)
        return

    # ── terminal dimensions ───────────────────────────────────────────────────
    term_w, term_h = get_terminal_size()
    width  = args.width  or min(term_w, 120)
    height = args.height or max(10, (width // 2) - 4)

    # ── save ASCII ────────────────────────────────────────────────────────────
    if args.save:
        rows  = render(width, height, objects, lights, cam, palette, args.depth)
        frame = "\n".join(rows)
        import re
        clean = re.sub(r"\x1b\[[^m]*m", "", frame)
        with open(args.save, "w") as f:
            f.write(f"raytracer.py — scene: {name}\n\n{clean}\n")
        print(f"saved to {args.save}")
        return

    # ── single frame ──────────────────────────────────────────────────────────
    if not args.anim:
        if args.color:
            rows = render_color(width, height, objects, lights, cam, palette, args.depth)
        else:
            rows = render(width, height, objects, lights, cam, palette, args.depth)
        print(f"\nraytracer.py  scene: {name}  {width}×{height}\n")
        print("\n".join(rows))
        return

    # ── animation loop ────────────────────────────────────────────────────────
    frame_time = 1.0 / args.fps
    t  = 0.0
    dt = 0.12

    clear_screen()
    hide_cursor()
    title = f"raytracer.py  scene: {name}  {width}×{height}  ctrl-c to quit"

    try:
        while True:
            t0 = time.perf_counter()
            objects, lights, cam = scene_fn(t)
            if args.color:
                rows = render_color(width, height, objects, lights, cam, palette, args.depth)
            else:
                rows = render(width, height, objects, lights, cam, palette, args.depth)
            print_frame(rows, title)
            elapsed = time.perf_counter() - t0
            time.sleep(max(0.0, frame_time - elapsed))
            t += dt
    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        print()


if __name__ == "__main__":
    main()
