from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterable, List, Optional


class OpCode(IntEnum):
    NOP = 0x00
    LDA_IMM = 0x10
    LDB_IMM = 0x11
    ADD_B = 0x20
    SUB_B = 0x21
    STA_ABS = 0x30
    JMP_ABS = 0x40
    JZ_ABS = 0x41
    PUSH_A = 0x50
    PUSH_B = 0x51
    POP_A = 0x52
    POP_B = 0x53
    CALL_ABS = 0x60
    RET = 0x61
    HLT = 0xFF


FLAG_Z = 0b0000_0001
FLAG_C = 0b0000_0010
FLAG_N = 0b0000_0100


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
        self.set_flag(FLAG_Z, value == 0)
        self.set_flag(FLAG_N, (value & 0x80) != 0)

    @staticmethod
    def opcode_name(opcode: int) -> str:
        try:
            return OpCode(opcode).name
        except ValueError:
            return f"UNKNOWN_0x{opcode:02X}"

    @staticmethod
    def opcode_size(opcode: int) -> int:
        if opcode in {OpCode.LDA_IMM, OpCode.LDB_IMM, OpCode.STA_ABS, OpCode.JMP_ABS, OpCode.JZ_ABS, OpCode.CALL_ABS}:
            return 2
        return 1

    @classmethod
    def decode_instruction_at(cls, ram: List[int], address: int) -> str:
        opcode = ram[address & 0xFF]
        next_byte = ram[(address + 1) & 0xFF]

        if opcode == OpCode.NOP:
            return "NOP"
        if opcode == OpCode.LDA_IMM:
            return f"LDA #0x{next_byte:02X}"
        if opcode == OpCode.LDB_IMM:
            return f"LDB #0x{next_byte:02X}"
        if opcode == OpCode.ADD_B:
            return "ADD B"
        if opcode == OpCode.SUB_B:
            return "SUB B"
        if opcode == OpCode.STA_ABS:
            return f"STA 0x{next_byte:02X}"
        if opcode == OpCode.JMP_ABS:
            return f"JMP 0x{next_byte:02X}"
        if opcode == OpCode.JZ_ABS:
            return f"JZ 0x{next_byte:02X}"
        if opcode == OpCode.PUSH_A:
            return "PUSH A"
        if opcode == OpCode.PUSH_B:
            return "PUSH B"
        if opcode == OpCode.POP_A:
            return "POP A"
        if opcode == OpCode.POP_B:
            return "POP B"
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

        if opcode == OpCode.LDA_IMM:
            self.a = self.fetch_byte()
            self.update_zero_and_negative(self.a)
            return

        if opcode == OpCode.LDB_IMM:
            self.b = self.fetch_byte()
            self.update_zero_and_negative(self.b)
            return

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

        if opcode == OpCode.STA_ABS:
            addr = self.fetch_byte()
            self.ram[addr] = self.a
            return

        if opcode == OpCode.JMP_ABS:
            addr = self.fetch_byte()
            self.pc = addr
            return

        if opcode == OpCode.JZ_ABS:
            addr = self.fetch_byte()
            if self.get_flag(FLAG_Z):
                self.pc = addr
            return

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

    def run(self, max_cycles: int = 1000, debug: bool = True) -> None:
        while not self.halted:
            if self.cycles >= max_cycles:
                raise RuntimeError("Maximum cycle count reached before HLT")
            self.step_cycle(debug=debug)


def build_test_program_add_store() -> List[int]:
    # LDA #7; LDB #5; CALL add; STA 0x0F; HLT; add: PUSH B; POP B; ADD B; RET
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
