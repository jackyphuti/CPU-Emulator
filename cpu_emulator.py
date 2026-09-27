from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Iterable, List, Optional


class OpCode(IntEnum):
    NOP = 0x00

    # Immediate operations (0x10..0x17)
    LDA_IMM = 0x10
    LDB_IMM = 0x11
    ADD_IMM = 0x12
    SUB_IMM = 0x13
    AND_IMM = 0x14
    OR_IMM = 0x15
    XOR_IMM = 0x16
    CMP_IMM = 0x17

    # Register ALU & Bitwise operations (0x20..0x2F)
    ADD_B = 0x20
    SUB_B = 0x21
    AND_B = 0x22
    OR_B = 0x23
    XOR_B = 0x24
    NOT_A = 0x25
    INC_A = 0x26
    DEC_A = 0x27
    INC_B = 0x28
    DEC_B = 0x29
    SHL_A = 0x2A
    SHR_A = 0x2B
    ROL_A = 0x2C
    ROR_A = 0x2D
    CMP_B = 0x2E
    TEST_B = 0x2F

    # Memory & Register Transfers (0x30..0x37)
    STA_ABS = 0x30
    LDA_ABS = 0x31
    LDB_ABS = 0x32
    STB_ABS = 0x33
    MOV_A_B = 0x34
    MOV_B_A = 0x35
    LDA_IND_B = 0x36
    STA_IND_B = 0x37

    # Jumps & Branches (0x40..0x46)
    JMP_ABS = 0x40
    JZ_ABS = 0x41
    JNZ_ABS = 0x42
    JC_ABS = 0x43
    JNC_ABS = 0x44
    JN_ABS = 0x45
    JNN_ABS = 0x46

    # Stack Operations (0x50..0x55)
    PUSH_A = 0x50
    PUSH_B = 0x51
    POP_A = 0x52
    POP_B = 0x53
    PUSHF = 0x54
    POPF = 0x55

    # Subroutine & Control (0x60..0xFF)
    CALL_ABS = 0x60
    RET = 0x61
    HLT = 0xFF


# CPU Flags
FLAG_Z = 0b0000_0001  # Zero flag
FLAG_C = 0b0000_0010  # Carry flag
FLAG_N = 0b0000_0100  # Negative flag (bit 7 set)

# Memory-Mapped I/O (MMIO) Ports
IO_PUTC = 0xF0    # Write ASCII character to console
IO_PUTNUM = 0xF1  # Write unsigned decimal number to console
IO_PUTHEX = 0xF2  # Write 2-digit hex number to console
IO_RND = 0xFE     # Read 8-bit pseudo-random value
IO_TICK = 0xFF    # Read lower 8 bits of CPU cycle counter

TWO_BYTE_OPCODES = {
    OpCode.LDA_IMM,
    OpCode.LDB_IMM,
    OpCode.ADD_IMM,
    OpCode.SUB_IMM,
    OpCode.AND_IMM,
    OpCode.OR_IMM,
    OpCode.XOR_IMM,
    OpCode.CMP_IMM,
    OpCode.STA_ABS,
    OpCode.LDA_ABS,
    OpCode.LDB_ABS,
    OpCode.STB_ABS,
    OpCode.JMP_ABS,
    OpCode.JZ_ABS,
    OpCode.JNZ_ABS,
    OpCode.JC_ABS,
    OpCode.JNC_ABS,
    OpCode.JN_ABS,
    OpCode.JNN_ABS,
    OpCode.CALL_ABS,
}


@dataclass
class CPU8Bit:
    ram: List[int] = field(default_factory=lambda: [0] * 256)
    pc: int = 0x00
    sp: int = 0xFF
    a: int = 0x00
    b: int = 0x00
    flags: int = 0x00
    ir: Optional[int] = None
    cycles: int = 0
    halted: bool = False
    _stack_depth: int = 0
    call_depth: int = 0
    io_output: List[str] = field(default_factory=list)
    on_io_output: Optional[Callable[[str, str], None]] = None

    def reset(self) -> None:
        self.ram = [0] * 256
        self.pc = 0x00
        self.sp = 0xFF
        self.a = 0x00
        self.b = 0x00
        self.flags = 0x00
        self.ir = None
        self.cycles = 0
        self.halted = False
        self._stack_depth = 0
        self.call_depth = 0
        self.io_output.clear()

    def load_program(self, program: Iterable[int], start_addr: int = 0x00, clear_ram: bool = True) -> None:
        bytes_to_load = list(program)
        if not 0 <= start_addr <= 0xFF:
            raise ValueError("Start address must be in range 0x00-0xFF")
        if start_addr + len(bytes_to_load) > 256:
            raise ValueError("Program does not fit in RAM")

        if clear_ram:
            self.ram = [0] * 256

        for offset, value in enumerate(bytes_to_load):
            if not 0 <= value <= 0xFF:
                raise ValueError(f"Program byte out of range: {value}")
            self.ram[start_addr + offset] = value

        self.pc = start_addr & 0xFF
        self.sp = 0xFF
        self.a = 0x00
        self.b = 0x00
        self.flags = 0x00
        self.ir = None
        self.cycles = 0
        self.halted = False
        self._stack_depth = 0
        self.call_depth = 0
        self.io_output.clear()

    def read_mem(self, addr: int) -> int:
        addr = addr & 0xFF
        if addr == IO_RND:
            return random.randint(0, 255)
        if addr == IO_TICK:
            return self.cycles & 0xFF
        return self.ram[addr]

    def write_mem(self, addr: int, val: int) -> None:
        addr = addr & 0xFF
        val = val & 0xFF
        self.ram[addr] = val

        # MMIO Handling
        if addr == IO_PUTC:
            char_str = chr(val)
            self.io_output.append(char_str)
            if self.on_io_output:
                self.on_io_output("char", char_str)
        elif addr == IO_PUTNUM:
            num_str = str(val)
            self.io_output.append(num_str)
            if self.on_io_output:
                self.on_io_output("num", num_str)
        elif addr == IO_PUTHEX:
            hex_str = f"{val:02X}"
            self.io_output.append(hex_str)
            if self.on_io_output:
                self.on_io_output("hex", hex_str)

    def fetch_byte(self) -> int:
        value = self.ram[self.pc]
        self.pc = (self.pc + 1) & 0xFF
        return value

    def push_byte(self, value: int) -> None:
        if self._stack_depth >= 256:
            raise RuntimeError("Stack overflow")
        self.ram[self.sp] = value & 0xFF
        self.sp = (self.sp - 1) & 0xFF
        self._stack_depth += 1

    def pop_byte(self) -> int:
        if self._stack_depth <= 0:
            raise RuntimeError("Stack underflow")
        self.sp = (self.sp + 1) & 0xFF
        value = self.ram[self.sp]
        self._stack_depth -= 1
        return value

    @property
    def stack_depth(self) -> int:
        return self._stack_depth

    def set_flag(self, flag_mask: int, enabled: bool) -> None:
        if enabled:
            self.flags |= flag_mask
        else:
            self.flags &= ~flag_mask

    def get_flag(self, flag_mask: int) -> bool:
        return (self.flags & flag_mask) != 0

    def update_zero_and_negative(self, value: int) -> None:
        self.set_flag(FLAG_Z, (value & 0xFF) == 0)
        self.set_flag(FLAG_N, (value & 0x80) != 0)

    @staticmethod
    def opcode_name(opcode: int) -> str:
        try:
            return OpCode(opcode).name
        except ValueError:
            return f"UNKNOWN_0x{opcode:02X}"

    @staticmethod
    def opcode_size(opcode: int) -> int:
        return 2 if opcode in TWO_BYTE_OPCODES else 1

    @classmethod
    def decode_instruction_at(cls, ram: List[int], address: int) -> str:
        opcode = ram[address & 0xFF]
        next_byte = ram[(address + 1) & 0xFF]

        if opcode == OpCode.NOP:
            return "NOP"

        # Immediate operations
        if opcode == OpCode.LDA_IMM:
            return f"LDA #0x{next_byte:02X}"
        if opcode == OpCode.LDB_IMM:
            return f"LDB #0x{next_byte:02X}"
        if opcode == OpCode.ADD_IMM:
            return f"ADD #0x{next_byte:02X}"
        if opcode == OpCode.SUB_IMM:
            return f"SUB #0x{next_byte:02X}"
        if opcode == OpCode.AND_IMM:
            return f"AND #0x{next_byte:02X}"
        if opcode == OpCode.OR_IMM:
            return f"OR #0x{next_byte:02X}"
        if opcode == OpCode.XOR_IMM:
            return f"XOR #0x{next_byte:02X}"
        if opcode == OpCode.CMP_IMM:
            return f"CMP #0x{next_byte:02X}"

        # Register ALU operations
        if opcode == OpCode.ADD_B:
            return "ADD B"
        if opcode == OpCode.SUB_B:
            return "SUB B"
        if opcode == OpCode.AND_B:
            return "AND B"
        if opcode == OpCode.OR_B:
            return "OR B"
        if opcode == OpCode.XOR_B:
            return "XOR B"
        if opcode == OpCode.NOT_A:
            return "NOT A"
        if opcode == OpCode.INC_A:
            return "INC A"
        if opcode == OpCode.DEC_A:
            return "DEC A"
        if opcode == OpCode.INC_B:
            return "INC B"
        if opcode == OpCode.DEC_B:
            return "DEC B"
        if opcode == OpCode.SHL_A:
            return "SHL A"
        if opcode == OpCode.SHR_A:
            return "SHR A"
        if opcode == OpCode.ROL_A:
            return "ROL A"
        if opcode == OpCode.ROR_A:
            return "ROR A"
        if opcode == OpCode.CMP_B:
            return "CMP B"
        if opcode == OpCode.TEST_B:
            return "TEST B"

        # Memory & Register Transfers
        if opcode == OpCode.STA_ABS:
            return f"STA 0x{next_byte:02X}"
        if opcode == OpCode.LDA_ABS:
            return f"LDA [0x{next_byte:02X}]"
        if opcode == OpCode.LDB_ABS:
            return f"LDB [0x{next_byte:02X}]"
        if opcode == OpCode.STB_ABS:
            return f"STB 0x{next_byte:02X}"
        if opcode == OpCode.MOV_A_B:
            return "MOV A, B"
        if opcode == OpCode.MOV_B_A:
            return "MOV B, A"
        if opcode == OpCode.LDA_IND_B:
            return "LDA [B]"
        if opcode == OpCode.STA_IND_B:
            return "STA [B]"

        # Jumps & Branches
        if opcode == OpCode.JMP_ABS:
            return f"JMP 0x{next_byte:02X}"
        if opcode == OpCode.JZ_ABS:
            return f"JZ 0x{next_byte:02X}"
        if opcode == OpCode.JNZ_ABS:
            return f"JNZ 0x{next_byte:02X}"
        if opcode == OpCode.JC_ABS:
            return f"JC 0x{next_byte:02X}"
        if opcode == OpCode.JNC_ABS:
            return f"JNC 0x{next_byte:02X}"
        if opcode == OpCode.JN_ABS:
            return f"JN 0x{next_byte:02X}"
        if opcode == OpCode.JNN_ABS:
            return f"JNN 0x{next_byte:02X}"

        # Stack operations
        if opcode == OpCode.PUSH_A:
            return "PUSH A"
        if opcode == OpCode.PUSH_B:
            return "PUSH B"
        if opcode == OpCode.POP_A:
            return "POP A"
        if opcode == OpCode.POP_B:
            return "POP B"
        if opcode == OpCode.PUSHF:
            return "PUSHF"
        if opcode == OpCode.POPF:
            return "POPF"

        # Subroutine & Control
        if opcode == OpCode.CALL_ABS:
            return f"CALL 0x{next_byte:02X}"
        if opcode == OpCode.RET:
            return "RET"
        if opcode == OpCode.HLT:
            return "HLT"

        return f"DB 0x{opcode:02X}"

    def execute_instruction(self, opcode: int) -> None:
        if opcode == OpCode.NOP:
            return

        # ---------------- Immediate Operations ----------------
        if opcode == OpCode.LDA_IMM:
            self.a = self.fetch_byte()
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.LDB_IMM:
            self.b = self.fetch_byte()
            self.update_zero_and_negative(self.b)
            return

        if opcode == OpCode.ADD_IMM:
            imm = self.fetch_byte()
            result = self.a + imm
            self.set_flag(FLAG_C, result > 0xFF)
            self.a = result & 0xFF
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.SUB_IMM:
            imm = self.fetch_byte()
            borrow = self.a < imm
            result = (self.a - imm) & 0xFF
            self.set_flag(FLAG_C, borrow)
            self.a = result
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.AND_IMM:
            imm = self.fetch_byte()
            self.a &= imm
            self.set_flag(FLAG_C, False)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.OR_IMM:
            imm = self.fetch_byte()
            self.a |= imm
            self.set_flag(FLAG_C, False)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.XOR_IMM:
            imm = self.fetch_byte()
            self.a ^= imm
            self.set_flag(FLAG_C, False)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.CMP_IMM:
            imm = self.fetch_byte()
            borrow = self.a < imm
            diff = (self.a - imm) & 0xFF
            self.set_flag(FLAG_C, borrow)
            self.update_zero_and_negative(diff)
            return

        # ---------------- Register ALU & Bitwise ----------------
        if opcode == OpCode.ADD_B:
            result = self.a + self.b
            self.set_flag(FLAG_C, result > 0xFF)
            self.a = result & 0xFF
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.SUB_B:
            borrow = self.a < self.b
            result = (self.a - self.b) & 0xFF
            self.set_flag(FLAG_C, borrow)
            self.a = result
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.AND_B:
            self.a &= self.b
            self.set_flag(FLAG_C, False)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.OR_B:
            self.a |= self.b
            self.set_flag(FLAG_C, False)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.XOR_B:
            self.a ^= self.b
            self.set_flag(FLAG_C, False)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.NOT_A:
            self.a = (~self.a) & 0xFF
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.INC_A:
            self.a = (self.a + 1) & 0xFF
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.DEC_A:
            self.a = (self.a - 1) & 0xFF
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.INC_B:
            self.b = (self.b + 1) & 0xFF
            self.update_zero_and_negative(self.b)
            return

        if opcode == OpCode.DEC_B:
            self.b = (self.b - 1) & 0xFF
            self.update_zero_and_negative(self.b)
            return

        if opcode == OpCode.SHL_A:
            bit7 = (self.a >> 7) & 1
            self.a = (self.a << 1) & 0xFF
            self.set_flag(FLAG_C, bit7 == 1)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.SHR_A:
            bit0 = self.a & 1
            self.a = (self.a >> 1) & 0xFF
            self.set_flag(FLAG_C, bit0 == 1)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.ROL_A:
            old_c = 1 if self.get_flag(FLAG_C) else 0
            new_c = (self.a >> 7) & 1
            self.a = ((self.a << 1) | old_c) & 0xFF
            self.set_flag(FLAG_C, new_c == 1)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.ROR_A:
            old_c = 1 if self.get_flag(FLAG_C) else 0
            new_c = self.a & 1
            self.a = ((self.a >> 1) | (old_c << 7)) & 0xFF
            self.set_flag(FLAG_C, new_c == 1)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.CMP_B:
            borrow = self.a < self.b
            diff = (self.a - self.b) & 0xFF
            self.set_flag(FLAG_C, borrow)
            self.update_zero_and_negative(diff)
            return

        if opcode == OpCode.TEST_B:
            val = self.a & self.b
            self.set_flag(FLAG_C, False)
            self.update_zero_and_negative(val)
            return

        # ---------------- Memory & Transfers ----------------
        if opcode == OpCode.STA_ABS:
            addr = self.fetch_byte()
            self.write_mem(addr, self.a)
            return

        if opcode == OpCode.LDA_ABS:
            addr = self.fetch_byte()
            self.a = self.read_mem(addr)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.LDB_ABS:
            addr = self.fetch_byte()
            self.b = self.read_mem(addr)
            self.update_zero_and_negative(self.b)
            return

        if opcode == OpCode.STB_ABS:
            addr = self.fetch_byte()
            self.write_mem(addr, self.b)
            return

        if opcode == OpCode.MOV_A_B:
            self.a = self.b
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.MOV_B_A:
            self.b = self.a
            self.update_zero_and_negative(self.b)
            return

        if opcode == OpCode.LDA_IND_B:
            self.a = self.read_mem(self.b)
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.STA_IND_B:
            self.write_mem(self.b, self.a)
            return

        # ---------------- Jumps & Branches ----------------
        if opcode == OpCode.JMP_ABS:
            addr = self.fetch_byte()
            self.pc = addr
            return

        if opcode == OpCode.JZ_ABS:
            addr = self.fetch_byte()
            if self.get_flag(FLAG_Z):
                self.pc = addr
            return

        if opcode == OpCode.JNZ_ABS:
            addr = self.fetch_byte()
            if not self.get_flag(FLAG_Z):
                self.pc = addr
            return

        if opcode == OpCode.JC_ABS:
            addr = self.fetch_byte()
            if self.get_flag(FLAG_C):
                self.pc = addr
            return

        if opcode == OpCode.JNC_ABS:
            addr = self.fetch_byte()
            if not self.get_flag(FLAG_C):
                self.pc = addr
            return

        if opcode == OpCode.JN_ABS:
            addr = self.fetch_byte()
            if self.get_flag(FLAG_N):
                self.pc = addr
            return

        if opcode == OpCode.JNN_ABS:
            addr = self.fetch_byte()
            if not self.get_flag(FLAG_N):
                self.pc = addr
            return

        # ---------------- Stack Operations ----------------
        if opcode == OpCode.PUSH_A:
            self.push_byte(self.a)
            return

        if opcode == OpCode.PUSH_B:
            self.push_byte(self.b)
            return

        if opcode == OpCode.POP_A:
            self.a = self.pop_byte()
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.POP_B:
            self.b = self.pop_byte()
            self.update_zero_and_negative(self.b)
            return

        if opcode == OpCode.PUSHF:
            self.push_byte(self.flags)
            return

        if opcode == OpCode.POPF:
            self.flags = self.pop_byte() & 0x07
            return

        # ---------------- Subroutine & Control ----------------
        if opcode == OpCode.CALL_ABS:
            addr = self.fetch_byte()
            return_addr = self.pc
            self.push_byte(return_addr)
            self.call_depth += 1
            self.pc = addr
            return

        if opcode == OpCode.RET:
            self.pc = self.pop_byte()
            self.call_depth = max(0, self.call_depth - 1)
            return

        if opcode == OpCode.HLT:
            self.halted = True
            return

        raise ValueError(f"Unknown opcode 0x{opcode:02X} at address 0x{(self.pc - 1) & 0xFF:02X}")

    def fetch_phase(self) -> int:
        if self.halted:
            raise RuntimeError("CPU is halted")
        if self.ir is not None:
            raise RuntimeError("Cannot fetch: instruction already fetched")
        self.ir = self.fetch_byte()
        return self.ir

    def decode_phase(self) -> str:
        if self.ir is None:
            raise RuntimeError("Cannot decode: no instruction fetched")
        return self.opcode_name(self.ir)

    def execute_phase(self) -> int:
        if self.ir is None:
            raise RuntimeError("Cannot execute: no instruction fetched")
        opcode = self.ir
        self.execute_instruction(opcode)
        self.ir = None
        self.cycles += 1
        return opcode

    def step_cycle(self, debug: bool = False) -> int:
        opcode = self.fetch_phase()
        self.decode_phase()
        executed_opcode = self.execute_phase()
        if debug:
            self.dump_state(cycle=self.cycles - 1, opcode=executed_opcode)
        return executed_opcode

    def dump_state(self, cycle: int, opcode: int) -> None:
        first_16 = " ".join(f"{b:02X}" for b in self.ram[:16])
        print(
            f"Cycle={cycle:03d} OPCODE=0x{opcode:02X} "
            f"PC=0x{self.pc:02X} SP=0x{self.sp:02X} "
            f"A=0x{self.a:02X} B=0x{self.b:02X} "
            f"FLAGS[ZCN]={int(self.get_flag(FLAG_Z))}{int(self.get_flag(FLAG_C))}{int(self.get_flag(FLAG_N))}"
        )
        print(f"RAM[00..0F]: {first_16}")

    def run(self, max_cycles: int = 100000, debug: bool = True) -> None:
        while not self.halted:
            if self.cycles >= max_cycles:
                raise RuntimeError("Maximum cycle count reached before HLT")
            self.step_cycle(debug=debug)


def build_test_program_add_store() -> List[int]:
    return [
        OpCode.LDA_IMM,
        0x07,
        OpCode.LDB_IMM,
        0x05,
        OpCode.CALL_ABS,
        0x09,
        OpCode.STA_ABS,
        0x0F,
        OpCode.HLT,
        OpCode.PUSH_B,
        OpCode.POP_B,
        OpCode.ADD_B,
        OpCode.RET,
    ]


def main() -> None:
    cpu = CPU8Bit()
    program = build_test_program_add_store()
    cpu.load_program(program, start_addr=0x00)
    cpu.run(debug=True)

    print("\nFinal result:")
    print(f"Memory[0x0F] = {cpu.ram[0x0F]} (expected 12)")


if __name__ == "__main__":
    main()
