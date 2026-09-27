# 8-Bit CPU Emulator & Systems Toolkit

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![C99](https://img.shields.io/badge/C-C99%20%2F%20C%2B%2B17-00599C?logo=c&logoColor=white)
![Performance](https://img.shields.io/badge/speed-180%2B%20MIPS-brightgreen)
![License](https://img.shields.io/github/license/jackyphuti/CPU-Emulator)

An educational and high-performance 8-bit CPU platform featuring an expanded Instruction Set Architecture (ISA), an interactive debugger UI with a live TTY console, a native high-speed C/C++ engine, and a built-in Mini-C compiler targeting 8-bit assembly.

---

## Highlights

- **256-Byte Byte-Addressable RAM** with dedicated MMIO ports and stack space.
- **Expanded Instruction Set Architecture (ISA)**:
  - Full arithmetic and bitwise logic (`ADD`, `SUB`, `AND`, `OR`, `XOR`, `NOT`, `INC`, `DEC`, `CMP`, `TEST`).
  - Bit shift & rotate operations (`SHL`, `SHR`, `ROL`, `ROR`).
  - Direct and indirect memory addressing (`LDA [addr]`, `STA [addr]`, `LDA [B]`, `STA [B]`, `MOV A, B`, `MOV B, A`).
  - Full conditional branching suite (`JZ`, `JNZ`, `JC`, `JNC`, `JN`, `JNN`, `JMP`).
  - Stack and subroutine support (`PUSH`, `POP`, `PUSHF`, `POPF`, `CALL`, `RET`).
  - Memory-Mapped I/O (`0xF0` Char Console, `0xF1` Decimal, `0xF2` Hex, `0xFE` RNG, `0xFF` Cycle Counter).
- **Native High-Speed C/C++ Core (`c_core/`)**:
  - Portable, zero-dependency C99 implementation running at **>180 MIPS (>180 MHz)**.
  - Interactive CLI debugger with step, run, breakpoints, memory hex viewer, and disassembler.
  - Complete native C unit test suite with 100% assertions passing.
  - Makefile and CMake build configurations with shared library support (`libcpu8.so`).
- **Built-in Mini-C Compiler (`c_compiler.py`)**:
  - Compiles a subset of C (functions, `int` variables, `if`/`else`, `while` loops, array indexing `arr[i]`, and MMIO I/O built-ins) directly into 8-bit assembly.
- **Enhanced Debugger UI (`cpu_ui.py`)**:
  - Live TTY MMIO console window for real-time text and numerical output.
  - One-click Example Program loader (Fibonacci, Bubble Sort, Factorial, Hello World, etc.).
  - Switchable Assembly vs. Mini-C editor modes.
  - Multi-speed execution controller (Slow, Normal, Fast, and Turbo / Max Speed).
  - Breakpoints, conditional breakpoints (e.g. `A==0x0C`), memory watch window, and live disassembly.

---

## Instruction Set Architecture (ISA)

| Opcode | Mnemonic | Size | Description | Flags |
|---|---|---|---|---|
| `0x00` | `NOP` | 1 | No operation | - |
| `0x10` | `LDA #imm` | 2 | Load immediate value into A | Z, N |
| `0x11` | `LDB #imm` | 2 | Load immediate value into B | Z, N |
| `0x12` | `ADD #imm` | 2 | A = A + immediate | Z, C, N |
| `0x13` | `SUB #imm` | 2 | A = A - immediate | Z, C, N |
| `0x14` | `AND #imm` | 2 | A = A & immediate | Z, C, N |
| `0x15` | `OR #imm` | 2 | A = A \| immediate | Z, C, N |
| `0x16` | `XOR #imm` | 2 | A = A ^ immediate | Z, C, N |
| `0x17` | `CMP #imm` | 2 | Compare A with immediate (A - imm) | Z, C, N |
| `0x20` | `ADD B` | 1 | A = A + B | Z, C, N |
| `0x21` | `SUB B` | 1 | A = A - B | Z, C, N |
| `0x22` | `AND B` | 1 | A = A & B | Z, C, N |
| `0x23` | `OR B` | 1 | A = A \| B | Z, C, N |
| `0x24` | `XOR B` | 1 | A = A ^ B | Z, C, N |
| `0x25` | `NOT A` | 1 | A = ~A | Z, N |
| `0x26` | `INC A` | 1 | A = A + 1 | Z, N |
| `0x27` | `DEC A` | 1 | A = A - 1 | Z, N |
| `0x28` | `INC B` | 1 | B = B + 1 | Z, N |
| `0x29` | `DEC B` | 1 | B = B - 1 | Z, N |
| `0x2A` | `SHL A` | 1 | Shift left A by 1 (Carry receives bit 7) | Z, C, N |
| `0x2B` | `SHR A` | 1 | Shift right A by 1 (Carry receives bit 0) | Z, C, N |
| `0x2C` | `ROL A` | 1 | Rotate left A through Carry | Z, C, N |
| `0x2D` | `ROR A` | 1 | Rotate right A through Carry | Z, C, N |
| `0x2E` | `CMP B` | 1 | Compare A with B (flags set, A unmodified) | Z, C, N |
| `0x2F` | `TEST B` | 1 | Test A with B (A & B, flags set) | Z, C, N |
| `0x30` | `STA addr` | 2 | Store A to RAM address | - |
| `0x31` | `LDA [addr]` | 2 | Load A from RAM address | Z, N |
| `0x32` | `LDB [addr]` | 2 | Load B from RAM address | Z, N |
| `0x33` | `STB addr` | 2 | Store B to RAM address | - |
| `0x34` | `MOV A, B` | 1 | Transfer B into A | Z, N |
| `0x35` | `MOV B, A` | 1 | Transfer A into B | Z, N |
| `0x36` | `LDA [B]` | 1 | Indirect load: A = RAM[B] | Z, N |
| `0x37` | `STA [B]` | 1 | Indirect store: RAM[B] = A | - |
| `0x40` | `JMP addr` | 2 | Unconditional jump to address | - |
| `0x41` | `JZ addr` | 2 | Jump if Zero flag is set (Z == 1) | - |
| `0x42` | `JNZ addr` | 2 | Jump if Zero flag is clear (Z == 0) | - |
| `0x43` | `JC addr` | 2 | Jump if Carry flag is set (C == 1) | - |
| `0x44` | `JNC addr` | 2 | Jump if Carry flag is clear (C == 0) | - |
| `0x45` | `JN addr` | 2 | Jump if Negative flag is set (N == 1) | - |
| `0x46` | `JNN addr` | 2 | Jump if Negative flag is clear (N == 0) | - |
| `0x50` | `PUSH A` | 1 | Push register A onto stack | - |
| `0x51` | `PUSH B` | 1 | Push register B onto stack | - |
| `0x52` | `POP A` | 1 | Pop top of stack into register A | Z, N |
| `0x53` | `POP B` | 1 | Pop top of stack into register B | Z, N |
| `0x54` | `PUSHF` | 1 | Push FLAGS register onto stack | - |
| `0x55` | `POPF` | 1 | Pop top of stack into FLAGS register | Z, C, N |
| `0x60` | `CALL addr` | 2 | Push return PC and jump to subroutine | - |
| `0x61` | `RET` | 1 | Pop return PC from stack | - |
| `0xFF` | `HLT` | 1 | Halt CPU execution | - |

---

## Memory Map

| Address Range | Purpose |
|---|---|
| `0x00 - 0xBF` | Program code & local variables |
| `0xC0 - 0xEF` | High RAM (arrays, data buffers, Mini-C static variables) |
| `0xF0` | **MMIO Console Character Output** (writing ASCII prints char) |
| `0xF1` | **MMIO Console Decimal Output** (writing byte prints unsigned decimal) |
| `0xF2` | **MMIO Console Hex Output** (writing byte prints 2-digit hex) |
| `0xFE` | **MMIO Hardware RNG** (reading yields pseudo-random byte) |
| `0xFF` | **MMIO Cycle Counter** (reading yields lower 8 bits of cycle count) |
| `0xFF` (downwards) | Hardware call and data stack (grows downwards from 0xFF) |

---

## Project Structure

```
CPU-Emulator/
├── c_core/                    # High-Performance Native C/C++ Engine
│   ├── cpu8.h                 # Core header, struct definitions, and C API
│   ├── cpu8.c                 # Cycle-accurate C implementation of 8-bit core
│   ├── main.c                 # Standalone interactive C CLI debugger & runner
│   ├── test_cpu8.c            # Comprehensive native C unit tests
│   ├── Makefile               # GNU Make build configuration
│   └── CMakeLists.txt         # Multi-platform CMake build configuration
├── examples/                  # Rich Suite of Assembly & C Programs
│   ├── 01_addition.asm        # Basic arithmetic & MMIO demo
│   ├── 02_fibonacci.asm       # Fibonacci sequence generator
│   ├── 03_multiplier.asm      # 8-bit software multiplier
│   ├── 04_bubble_sort.asm     # In-place RAM array bubble sort
│   ├── 05_hello_world.asm     # Null-terminated string printer
│   ├── 06_factorial.asm       # Recursive factorial with call frames
│   ├── 07_bitwise_demo.asm    # Logical & bit shift operations
│   └── c_programs/            # Mini-C Sample Source Files
│       ├── fibonacci.c        # Fibonacci sequence in C
│       ├── sum_array.c        # Array indexing and summing in C
│       └── counter.c          # While-loop counter in C
├── assembler.py               # 2-pass assembler supporting DB strings & DW
├── c_compiler.py              # Mini-C compiler targeting 8-bit assembly
├── cpu_emulator.py            # Reference cycle-accurate Python CPU core
├── cpu_ui.py                  # Tkinter UI with TTY console & speed control
├── test_emulator.py           # Python unit tests for CPU, assembler & compiler
└── README.md
```

---

## Quick Start

### 1. Launch the Interactive GUI Debugger

```powershell
python cpu_ui.py
```

- Select any program from the **Load Example** dropdown (e.g. *In-Place Bubble Sort* or *Fibonacci (Mini-C)*).
- Click **ASSEMBLE + LOAD** (or **COMPILE C & LOAD**).
- Use **STEP** to step through cycle-by-cycle, or set **Speed** to **Turbo** and click **RUN**.
- Observe computed values in the **TTY CONSOLE** and **RAM VIEW**!

---

### 2. Mini-C Compiler: Write C, Run on 8-bit Hardware

Compile and execute C code directly on the 8-bit emulator:

```powershell
# Compile C file to 8-bit assembly:
python c_compiler.py examples/c_programs/fibonacci.c -o fib.asm

# Compile and execute immediately in emulator:
python c_compiler.py examples/c_programs/fibonacci.c --run
```

**Example Mini-C program (`fibonacci.c`):**
```c
void main() {
    int a = 0;
    int b = 1;
    int n = 7;
    int t = 0;

    while (n > 0) {
        print_num(a);
        putchar(32); // Space ' '
        t = a + b;
        a = b;
        b = t;
        n = n - 1;
    }
    putchar(10); // Newline
}
```

---

### 3. Native C/C++ Engine (`c_core/`)

The native engine is written in standard C99/C++17 with zero third-party dependencies.

#### Build and Run Tests (Linux / WSL / macOS):
```bash
cd c_core
make test
```

#### Run Performance Benchmark (>180 MIPS):
```bash
cd c_core
make bench
```

#### Interactive C CLI Debugger:
```bash
./c_core/cpu8_cli [program.bin]
```

Interactive commands:
- `s` / `step`: Execute one instruction and inspect registers.
- `r` / `run`: Run continuously until HLT or breakpoint.
- `bp <addr>` / `del <addr>`: Add/remove breakpoint.
- `reg`: Inspect PC, SP, A, B, FLAGS, and stack depth.
- `mem <addr> [count]`: Memory dump in hexadecimal and ASCII.
- `dis [addr] [count]`: Disassemble memory.
- `trace`: Toggle real-time execution trace.
- `q`: Exit.

---

### 4. Running Python Test Suites

Run all 13 comprehensive Python unit tests (verifying ALU, bit shifts, flags, MMIO, subroutines, assembler, and Mini-C compiler):

```powershell
python test_emulator.py
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
