# 8-bit CPU Emulator

A custom 8-bit CPU emulator with stack operations, assembler support, and an interactive UI.

## Features

- 256-byte RAM, byte-addressable
- Registers: `PC`, `SP`, `A`, `B`, `IR`, `FLAGS`
- Flags: Zero (`Z`), Carry (`C`), Negative (`N`)
- Full fetch-decode-execute cycle
- Phase control methods: `fetch_phase`, `decode_phase`, `execute_phase`
- Stack and subroutine support using SP
- Text assembler with labels, numeric literals, and directives
- Interactive GUI with register/control/memory/debug panels

## ISA and Opcodes

- `NOP` = `0x00`
- `LDA [imm]` = `0x10`
- `LDB [imm]` = `0x11`
- `ADD B` = `0x20`
- `SUB B` = `0x21`
- `STA [addr]` = `0x30`
- `JMP [addr]` = `0x40`
- `JZ [addr]` = `0x41`
- `PUSH A` = `0x50`
- `PUSH B` = `0x51`
- `POP A` = `0x52`
- `POP B` = `0x53`
- `CALL [addr]` = `0x60`
- `RET` = `0x61`
- `HLT` = `0xFF`

## Files

- `cpu_emulator.py`: core CPU model and CLI test run
- `assembler.py`: mnemonic assembler (`assemble`, `assemble_file`)
- `program.asm`: example assembly source
- `cpu_ui.py`: interactive UI layer on top of the core emulator

## Run CLI Demo

```powershell
python cpu_emulator.py
```

The default test program executes arithmetic through a subroutine and stores the final value at address `0x0F`.

## Assemble Mnemonics

Use Python directly:

```powershell
python -c "from assembler import assemble_file; print(assemble_file('program.asm'))"
```

Supported syntax:

- Labels: `loop:`
- Immediate and address values: `#10`, `0x0F`, `15`, `0b1010`
- Constants: `.EQU NAME 0x0F`
- Relocation: `.ORG 0x40`
- Comments: `; this is a comment`
- Data bytes: `DB 0x10 0xFF 20`

## Run Interactive UI

```powershell
python cpu_ui.py
```

UI controls include:

- `FETCH`, `DECODE`, `EXECUTE` (phase-by-phase stepping)
- `STEP` (single full cycle)
- `RUN` (continuous stepping)
- `RUN TO ADDRESS` (run until PC reaches target)
- `ASSEMBLE + LOAD` (compiles source editor into RAM)
- `RESET` (clears RAM and registers)

Debugger features include:

- Address breakpoints and double-click breakpoints in live disassembly
- Conditional breakpoints (for example `A==0x0C`, `CYCLE>=10`, `Z==1`)
- Stack window and memory watch window
- Instruction trace (mnemonic + operands per executed cycle)
- Live disassembly view around current PC
