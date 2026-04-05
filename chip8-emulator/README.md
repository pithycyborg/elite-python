# CHIP-8 Emulator

One file. Zero third-party dependencies. Explicit control.

This project is a reference implementation of the CHIP-8 virtual machine, written in pure Python 3 and using only the standard-library `curses` module for terminal output. It is designed to run on a typical Linux system without installing external packages.

## Purpose

CHIP-8 is a small interpreted system that is useful for studying instruction decoding, timing, memory layout, and framebuffer updates. This project exists as a compact, readable implementation of those mechanisms.

It is intended for engineers, students, and hobbyists who want to study emulation and low-level program structure in a minimal environment.

## Technical Overview

This implementation models the classic CHIP-8 environment:

- Memory: 4096 bytes.
- Registers: 16 general-purpose 8-bit registers, `V0` through `VF`.
- Stack: Support for nested subroutine calls.
- Graphics: 64 × 32 monochrome display using XOR sprite drawing.
- Timers: Delay and sound timers updated at 60 Hz.
- Input: 16-key hexadecimal keypad.

## Implementation Notes

- Opcode decoding uses bit masking and nibble extraction.
- CPU execution and timer updates are separated so timing remains stable across host systems.
- Rendering is handled through `curses`, which keeps the interface portable and avoids external graphics libraries.

## How to Run

1. Obtain a compatible `.ch8` ROM file, such as `PONG.ch8`.
2. Run the emulator:

```bash
python3 chip8.py path/to/rom.ch8
```

## Controls

The keypad mapping follows the standard CHIP-8 layout:

```text
1 2 3 4
q w e r
a s d f
z x c v
```

## Notes on Scope

This project targets the original CHIP-8 instruction set and terminal rendering only. It does not aim to implement later variants such as Super-CHIP or SCHIP-compatible display extensions.

## Disclaimer

This project is intended for educational use. It emphasizes clarity, correctness, and minimal dependencies.

## Status

Stable

## Author

Pithy Cyborg

## License

MIT

## Links

- **Newsletter: https://pithycyborg.com**
- **Twitter/X 1: https://x.com/mrcomputersci**
- **Twitter/X 2: https://x.com/pithycyborg**
- **Substack: https://pithycyborg.substack.com/subscribe**
