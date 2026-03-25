# CPU Emulator (8-bit)

An educational 8-bit CPU emulator with a built-in assembler and an interactive debugger-style UI.

## Preview

![CPU Emulator UI](Visual%20CPU%20EMULATOR.png)

## Highlights

- 256-byte, byte-addressable RAM
- Registers: PC, SP, A, B, IR, FLAGS
- Flags: Z (Zero), C (Carry), N (Negative)
- Full fetch-decode-execute cycle support
- Stack operations and subroutine flow (PUSH/POP, CALL/RET)
- Assembler with labels plus .ORG and .EQU directives
- Debugger UI with breakpoints, conditional breakpoints, trace, watches, and live disassembly

## Instruction Set

- NOP = 0x00
- LDA imm = 0x10
- LDB imm = 0x11
- ADD B = 0x20
- SUB B = 0x21
- STA addr = 0x30
- JMP addr = 0x40
- JZ addr = 0x41
- PUSH A = 0x50
- PUSH B = 0x51
- POP A = 0x52
- POP B = 0x53
- CALL addr = 0x60
- RET = 0x61
- HLT = 0xFF

## Project Files

- cpu_emulator.py: CPU core, ISA execution, stack/call behavior
- assembler.py: assembly parser and bytecode generator
- cpu_ui.py: interactive emulator and debugger UI
- program.asm: sample program source

## Quick Start

1. Create and activate a Python virtual environment (optional but recommended).
2. Run the UI:

```powershell
python cpu_ui.py
```

3. In the UI, click ASSEMBLE + LOAD, then STEP or RUN.

## Demo Workflow

1. Assemble default source with ASSEMBLE + LOAD.
2. Use STEP to inspect each cycle.
3. Add a breakpoint (for example 0x09) and click RUN.
4. Add a conditional breakpoint (for example A==0x0C).
5. Track watched memory addresses from the watch window.
6. Use RUN TO ADDRESS to pause at a target PC.

## Assembler Notes

Supported syntax examples:

- Labels: loop:
- Immediate values: #10, #0x0F
- Numeric literals: 15, 0x0F, 0b1010
- Constants: .EQU OUT_ADDR 0x0F
- Relocation: .ORG 0x40
- Data bytes: DB 0x10 0xFF 20
- Comments: ; comment text

Example command:

```powershell
python -c "from assembler import assemble_file; print(assemble_file('program.asm'))"
```

## CLI Mode

For cycle dump output in terminal:

```powershell
python cpu_emulator.py
```
