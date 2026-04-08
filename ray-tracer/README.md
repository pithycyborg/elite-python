# Ray Tracer

**One file. Zero third-party dependencies. Real-time terminal + real PNGs.**

A complete, from-scratch ray tracer written in pure Python 3. Renders spheres, planes, point lights, shadows, reflections, and full Blinn-Phong shading, straight to your terminal in ASCII or 24-bit color, or to proper binary PPM/PNG files using only the stdlib (`zlib` + `struct`).

Built as a high-signal educational project: clean math, proper ray tracing pipeline, and a minimal but correct PNG encoder in < 600 lines.

## Purpose

This project exists to show that you can build a visually impressive, physically-based renderer with nothing but the Python standard library. It is designed for engineers, students, and hobbyists who want to deeply understand:

- Vector math and ray-object intersection
- Recursive path tracing (shadows + reflections)
- Blinn-Phong shading model
- Binary image file formats (PPM + full PNG with DEFLATE)
- Terminal-first UX with zero external dependencies

Perfect companion to low-level systems projects (see my [CHIP-8 emulator]([https://github.com/pithycyborg/chip8](https://github.com/pithycyborg/elite-python/tree/main/chip8-emulator))).

## Features

- **Three animated scenes** (classic spheres, orbiting solar system, reflective corridor)
- **Terminal rendering**: ASCII art + optional 24-bit ANSI color
- **Image export**: PPM and **real PNG** (no Pillow, no external libs)
- **Real-time animation** with stable frame timing
- **Recursive reflections** (configurable depth)
- **Shadows**, ambient/diffuse/specular, gamma correction
- **Zero dependencies** | runs anywhere Python 3 runs

## Technical Overview

- **Math**: Custom `Vec3` with operator overloading, ray casting, sphere/plane intersection
- **Shading**: Full Blinn-Phong + shadow rays + recursive reflection
- **Camera**: Perspective with FOV and aspect-ratio correction for terminal
- **Output**:
  - Terminal: luminance-based ASCII palette (dense or simple)
  - PNG: Pure stdlib implementation (IHDR, IDAT with zlib, proper scanline filtering)
- **Performance**: Single-threaded but fast enough for 1280×720 PNGs in seconds

## How to Run

```bash
# Terminal ASCII (default)
python3 raytracer.py

# Animated solar system in color
python3 raytracer.py --scene 2 --anim --color

# Wide terminal render
python3 raytracer.py --width 180 --dense

# Export high-res PNG (pure stdlib)
python3 raytracer.py --png solar.png --img-width 1280 --img-height 720 --scene 2

# Export PPM
python3 raytracer.py --ppm classic.ppm --img-width 800 --img-height 450
```

**All scenes** (use `--scene 1|2|3`):
- **1** | Classic (chrome + matte spheres on plane)
- **2** | Solar system (orbiting planets + sun)
- **3** | Reflective corridor (abstract shiny balls)

Full CLI help:
```bash
python3 raytracer.py --help
```

## Implementation Notes

- Opcode-style clarity: every major stage (`trace`, `shade`, `nearest_hit`) is a short, readable function.
- PNG writer is self-contained and correct | implements signature, IHDR, IDAT (zlib-compressed), IEND, and CRC32.
- Terminal aspect ratio is corrected (characters are ~2× taller than wide).
- Gamma correction is applied consistently for both ASCII and image output.

## Notes on Scope

Intentionally minimal: only spheres, planes, and point lights. No textures, no BVH, no Monte-Carlo path tracing. The goal is maximum educational value and "it just works" polish in a single file.

## Status

**Stable** | polished, well-tested, and ready to run or extend.

## Author

**Pithy Cyborg**

## License

MIT

## Links

- **Newsletter**: https://pithycyborg.com/newsletter
- **Twitter/X 1**: https://x.com/mrcomputersci
- **Twitter/X 2**: https://x.com/pithycyborg
- **Substack**: https://pithycyborg.substack.com/subscribe

---

Built for people who like to understand things from first principles.  
Star it if you learned something... or better yet, build the next one with me.
```
