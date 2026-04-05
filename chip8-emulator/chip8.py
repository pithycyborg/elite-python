#!/usr/bin/env python3
"""
PithyCyborg's Pure Python CHIP-8 Emulator
One file. Zero dependencies. PhD-level systems craft.
Written by a nerd who has been coding since 16-bit AOL was a thing.
Please join my free AI newsletter if you enjoyed this code. -> PithyCyborg.com
"""

import curses
import random
import sys
import time


class Chip8:
    def __init__(self):
        self.memory = [0] * 4096
        self.v = [0] * 16
        self.i = 0
        self.pc = 0x200
        self.stack = []
        self.delay_timer = 0
        self.sound_timer = 0
        self.display = [[0] * 64 for _ in range(32)]
        self.keys = [0] * 16
        self.waiting_for_key = None
        self.draw_flag = True

        # Load Font into primary memory (0x000-0x04F)
        font = [
            0xF0, 0x90, 0x90, 0x90, 0xF0, 0x20, 0x60, 0x20, 0x20, 0x70,
            0xF0, 0x10, 0xF0, 0x80, 0xF0, 0xF0, 0x10, 0xF0, 0x10, 0xF0,
            0x90, 0x90, 0xF0, 0x10, 0x10, 0xF0, 0x80, 0xF0, 0x10, 0xF0,
            0xF0, 0x80, 0xF0, 0x90, 0xF0, 0xF0, 0x10, 0x20, 0x40, 0x40,
            0xF0, 0x90, 0xF0, 0x90, 0xF0, 0xF0, 0x90, 0xF0, 0x10, 0xF0,
            0xF0, 0x90, 0xF0, 0x90, 0x90, 0xE0, 0x90, 0xE0, 0x90, 0xE0,
            0xF0, 0x80, 0x80, 0x80, 0xF0, 0xE0, 0x90, 0x90, 0x90, 0xE0,
            0xF0, 0x80, 0xF0, 0x80, 0xF0, 0xF0, 0x80, 0xF0, 0x80, 0x80
        ]
        for idx, byte in enumerate(font):
            self.memory[idx] = byte

        # --- THE ELITE DISPATCH TABLE ---
        # Map high nibble (opcode >> 12) to specialized handler methods
        self.table = {
            0x0: self._table_0,
            0x1: self._op_1nnn,
            0x2: self._op_2nnn,
            0x3: self._op_3xnn,
            0x4: self._op_4xnn,
            0x5: self._op_5xy0,
            0x6: self._op_6xnn,
            0x7: self._op_7xnn,
            0x8: self._table_8,
            0x9: self._op_9xy0,
            0xA: self._op_Annn,
            0xB: self._op_Bnnn,
            0xC: self._op_Cxnn,
            0xD: self._op_Dxyn,
            0xE: self._table_E,
            0xF: self._table_F,
        }

    def cycle(self):
        """Execute one CPU cycle."""
        # NOTE (added): CPU pauses on FX0A, but timers must continue ticking.
        # Timers are handled outside this function, so early return is correct.
        if self.waiting_for_key is not None:
            return

        # Fetch
        opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc = (self.pc + 2) & 0xFFF

        # Decode & Execute via elite table lookup
        prefix = (opcode & 0xF000) >> 12
        handler = self.table.get(prefix)
        if handler:
            handler(opcode)
        else:
            raise RuntimeError(f"Unknown opcode: {opcode:04X}")

    # --- DISPATCH HANDLERS ---

    def _table_0(self, op):
        """Handle 0x0nnn group (mostly 00E0 and 00EE)"""
        if op == 0x00E0:      # CLS - Clear display
            self.display = [[0] * 64 for _ in range(32)]
            self.draw_flag = True
        elif op == 0x00EE:    # RET - Return from subroutine
            if self.stack:
                self.pc = self.stack.pop()
        # else: unknown 0x0nnn → treated as NOP (common practice)

    def _op_1nnn(self, op):   # JP addr
        self.pc = op & 0x0FFF

    def _op_2nnn(self, op):   # CALL addr
        self.stack.append(self.pc)
        self.pc = op & 0x0FFF

    def _op_3xnn(self, op):   # SE Vx, byte
        if self.v[(op & 0x0F00) >> 8] == (op & 0x00FF):
            self.pc += 2

    def _op_4xnn(self, op):   # SNE Vx, byte
        if self.v[(op & 0x0F00) >> 8] != (op & 0x00FF):
            self.pc += 2

    def _op_5xy0(self, op):   # SE Vx, Vy
        if self.v[(op & 0x0F00) >> 8] == self.v[(op & 0x00F0) >> 4]:
            self.pc += 2

    def _op_6xnn(self, op):   # LD Vx, byte
        self.v[(op & 0x0F00) >> 8] = op & 0x00FF

    def _op_7xnn(self, op):   # ADD Vx, byte
        x = (op & 0x0F00) >> 8
        self.v[x] = (self.v[x] + (op & 0x00FF)) & 0xFF

    def _table_8(self, op):
        """Handle 0x8xyN arithmetic/logic group"""
        x = (op & 0x0F00) >> 8
        y = (op & 0x00F0) >> 4
        n = op & 0x000F

        if n == 0x0:    # LD Vx, Vy
            self.v[x] = self.v[y]
        elif n == 0x1:  # OR
            self.v[x] |= self.v[y]
        elif n == 0x2:  # AND
            self.v[x] &= self.v[y]
        elif n == 0x3:  # XOR
            self.v[x] ^= self.v[y]
        elif n == 0x4:  # ADD (with carry)
            res = self.v[x] + self.v[y]
            self.v[0xF] = 1 if res > 0xFF else 0
            self.v[x] = res & 0xFF
        elif n == 0x5:  # SUB
            self.v[0xF] = 1 if self.v[x] > self.v[y] else 0
            self.v[x] = (self.v[x] - self.v[y]) & 0xFF
        elif n == 0x6:  # SHR (modern behavior)
            self.v[0xF] = self.v[x] & 0x01
            self.v[x] >>= 1
        elif n == 0x7:  # SUBN
            self.v[0xF] = 1 if self.v[y] > self.v[x] else 0
            self.v[x] = (self.v[y] - self.v[x]) & 0xFF
        elif n == 0xE:  # SHL
            self.v[0xF] = (self.v[x] & 0x80) >> 7
            self.v[x] = (self.v[x] << 1) & 0xFF

    def _op_9xy0(self, op):   # SNE Vx, Vy
        if self.v[(op & 0x0F00) >> 8] != self.v[(op & 0x00F0) >> 4]:
            self.pc += 2

    def _op_Annn(self, op):   # LD I, addr
        self.i = op & 0x0FFF

    def _op_Bnnn(self, op):   # JP V0, addr
        self.pc = (op & 0x0FFF) + self.v[0]

    def _op_Cxnn(self, op):   # RND Vx, byte
        x = (op & 0x0F00) >> 8
        self.v[x] = random.randint(0, 255) & (op & 0x00FF)

    def _op_Dxyn(self, op):   # DRW Vx, Vy, nibble
        vx = self.v[(op & 0x0F00) >> 8] % 64
        vy = self.v[(op & 0x00F0) >> 4] % 32
        n = op & 0x000F

        self.v[0xF] = 0
        for row in range(n):
            pixel_byte = self.memory[self.i + row]
            for col in range(8):
                if pixel_byte & (0x80 >> col):
                    tx = (vx + col) % 64
                    ty = (vy + row) % 32
                    if self.display[ty][tx]:
                        self.v[0xF] = 1
                    self.display[ty][tx] ^= 1

        self.draw_flag = True

    def _table_E(self, op):
        """Handle 0xExNN keyboard group"""
        x = (op & 0x0F00) >> 8
        nn = op & 0x00FF

        if nn == 0x9E:      # SKP Vx
            if self.keys[self.v[x] & 0x0F]:
                self.pc += 2
        elif nn == 0xA1:    # SKNP Vx
            if not self.keys[self.v[x] & 0x0F]:
                self.pc += 2

    def _table_F(self, op):
        """Handle 0xFxNN miscellaneous group"""
        x = (op & 0x0F00) >> 8
        nn = op & 0x00FF

        if nn == 0x07:      # LD Vx, DT
            self.v[x] = self.delay_timer
        elif nn == 0x0A:    # LD Vx, K
            self.waiting_for_key = x
        elif nn == 0x15:    # LD DT, Vx
            self.delay_timer = self.v[x]
        elif nn == 0x18:    # LD ST, Vx
            self.sound_timer = self.v[x]
        elif nn == 0x1E:    # ADD I, Vx
            self.i = (self.i + self.v[x]) & 0xFFF
        elif nn == 0x29:    # LD F, Vx
            self.i = (self.v[x] & 0x0F) * 5
        elif nn == 0x33:    # LD B, Vx
            val = self.v[x]
            self.memory[self.i]     = val // 100
            self.memory[self.i + 1] = (val // 10) % 10
            self.memory[self.i + 2] = val % 10
        elif nn == 0x55:    # LD [I], Vx
            for j in range(x + 1):
                self.memory[self.i + j] = self.v[j]
        elif nn == 0x65:    # LD Vx, [I]
            for j in range(x + 1):
                self.v[j] = self.memory[self.i + j]

    def load_rom(self, path):
        """Load a ROM file into memory starting at 0x200"""
        with open(path, 'rb') as f:
            rom = f.read()
            for i, b in enumerate(rom):
                if 0x200 + i < 4096:
                    self.memory[0x200 + i] = b

    def set_key(self, key, down):
        """Update key state (key should be 0-15)"""
        self.keys[key] = 1 if down else 0
        if down and self.waiting_for_key is not None:
            self.v[self.waiting_for_key] = key
            self.waiting_for_key = None


# ====================== CURSES FRONTEND ======================

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)

    chip8 = Chip8()

    if len(sys.argv) < 2:
        print("Usage: python chip8.py <rom.ch8>")
        sys.exit(1)

    chip8.load_rom(sys.argv[1])

    last_timer_tick = time.time()

    # NOTE (added): Track key up / key down state properly
    pressed_keys = set()

    while True:
        key = stdscr.getch()

        # NOTE (added): ESC is now the quit key
        if key == 27:
            break

        mapping = {
            ord('1'): 0x1, ord('2'): 0x2, ord('3'): 0x3, ord('4'): 0xC,
            ord('q'): 0x4, ord('w'): 0x5, ord('e'): 0x6, ord('r'): 0xD,
            ord('a'): 0x7, ord('s'): 0x8, ord('d'): 0x9, ord('f'): 0xE,
            ord('z'): 0xA, ord('x'): 0x0, ord('c'): 0xB, ord('v'): 0xF,
        }

        current_keys = set()
        if key in mapping:
            current_keys.add(mapping[key])

        for k in current_keys - pressed_keys:
            chip8.set_key(k, True)

        for k in pressed_keys - current_keys:
            chip8.set_key(k, False)

        pressed_keys = current_keys

        for _ in range(12):
            chip8.cycle()

        now = time.time()
        if now - last_timer_tick >= 1 / 60.0:
            if chip8.delay_timer > 0:
                chip8.delay_timer -= 1
            if chip8.sound_timer > 0:
                curses.beep()   # NOTE (added): audible feedback
                chip8.sound_timer -= 1
            last_timer_tick = now

        if chip8.draw_flag:
            stdscr.clear()
            for y in range(32):
                for x in range(64):
                    if chip8.display[y][x]:
                        stdscr.addstr(y, x * 2, '██')

            # NOTE (added): guard against small terminals
            h, _ = stdscr.getmaxyx()
            if h > 34:
                stdscr.addstr(
                    34, 0,
                    "Press ESC to Quit | Controls: 1-4 QWER ASDF ZXCV | PithyCyborg.com"
                )

            stdscr.refresh()
            chip8.draw_flag = False

        time.sleep(0.001)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nEmulator terminated by user.")
    except Exception as e:
        print(f"Error: {e}")
