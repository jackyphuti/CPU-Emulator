from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from cpu_emulator import OpCode


class AssemblerError(ValueError):
    pass


@dataclass
class ParsedLine:
    line_no: int
    label: Optional[str]
    mnemonic: Optional[str]
    operands: List[str]


ZERO_OPERAND_OPS = {
    "NOP": OpCode.NOP,
    "HLT": OpCode.HLT,
    "RET": OpCode.RET,
    "PUSHF": OpCode.PUSHF,
    "POPF": OpCode.POPF,
    "TEST": OpCode.TEST_B,
}

BRANCH_OPS = {
    "JMP": OpCode.JMP_ABS,
    "JZ": OpCode.JZ_ABS,
    "JNZ": OpCode.JNZ_ABS,
    "JC": OpCode.JC_ABS,
    "JNC": OpCode.JNC_ABS,
    "JN": OpCode.JN_ABS,
    "JNN": OpCode.JNN_ABS,
    "CALL": OpCode.CALL_ABS,
}


def _strip_comment(line: str) -> str:
    semicolon_split = line.split(";", maxsplit=1)[0]
    slash_split = semicolon_split.split("//", maxsplit=1)[0]
    return slash_split.strip()


def _tokenize(line: str) -> List[str]:
    tokens: List[str] = []
    current: List[str] = []
    in_quote = False
    quote_char = ""

    for char in line:
        if in_quote:
            current.append(char)
            if char == quote_char:
                in_quote = False
        elif char in ('"', "'"):
            in_quote = True
            quote_char = char
            current.append(char)
        elif char in (",", " ", "\t"):
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)

    if current:
        tokens.append("".join(current))

    return tokens


def _parse_number(token: str, max_val: int = 0xFF) -> int:
    token = token.strip()
    if token.startswith("#"):
        token = token[1:]

    # Character literal: 'A'
    if (token.startswith("'") and token.endswith("'")) and len(token) >= 3:
        val = ord(token[1:-1].encode("utf-8").decode("unicode_escape")[0])
        return val & max_val

    if token.lower().startswith("0x"):
        value = int(token, 16)
    elif token.lower().startswith("0b"):
        value = int(token, 2)
    elif token.lower().endswith("h") and len(token) > 1:
        value = int(token[:-1], 16)
    else:
        value = int(token, 10)

    if not 0 <= value <= max_val:
        raise AssemblerError(f"Value out of range (0-{max_val}): {value}")
    return value


def _resolve_operand(token: str, labels: Dict[str, int], constants: Dict[str, int], line_no: int, max_val: int = 0xFF) -> int:
    token = token.strip()
    if token.startswith("#"):
        token = token[1:].strip()
    if token.startswith("[") and token.endswith("]"):
        token = token[1:-1].strip()

    if token in constants:
        return constants[token]

    if token in labels:
        return labels[token]

    try:
        return _parse_number(token, max_val=max_val)
    except ValueError as exc:
        raise AssemblerError(f"Line {line_no}: unknown label or invalid number '{token}'") from exc


def _parse_source(source: str) -> List[ParsedLine]:
    parsed: List[ParsedLine] = []

    for line_no, raw_line in enumerate(source.splitlines(), start=1):
        clean = _strip_comment(raw_line)
        if not clean:
            continue

        tokens = _tokenize(clean)
        if not tokens:
            continue

        label = None
        if tokens[0].endswith(":"):
            label = tokens[0][:-1].strip()
            if not label:
                raise AssemblerError(f"Line {line_no}: empty label")
            tokens = tokens[1:]

        if not tokens:
            parsed.append(ParsedLine(line_no=line_no, label=label, mnemonic=None, operands=[]))
            continue

        mnemonic = tokens[0].upper()
        operands = tokens[1:]
        parsed.append(ParsedLine(line_no=line_no, label=label, mnemonic=mnemonic, operands=operands))

    return parsed


def _unescape_string(s: str) -> bytes:
    content = s[1:-1]
    return content.encode("utf-8").decode("unicode_escape").encode("latin1", "replace")


def _instruction_size(item: ParsedLine) -> int:
    if item.mnemonic is None:
        return 0

    mnemonic = item.mnemonic

    if mnemonic in {".ORG", ".EQU"}:
        return 0

    if mnemonic == "DB":
        if not item.operands:
            raise AssemblerError(f"Line {item.line_no}: DB requires at least one operand")
        size = 0
        for op in item.operands:
            if (op.startswith('"') and op.endswith('"')) or (op.startswith("'") and op.endswith("'")):
                size += len(_unescape_string(op))
            else:
                size += 1
        return size

    if mnemonic == "DW":
        if not item.operands:
            raise AssemblerError(f"Line {item.line_no}: DW requires at least one operand")
        return len(item.operands) * 2

    if mnemonic in ZERO_OPERAND_OPS:
        return 1

    if mnemonic in BRANCH_OPS:
        return 2

    if mnemonic in {"PUSH", "POP"}:
        return 1

    if mnemonic == "MOV":
        return 1

    if mnemonic in {"NOT", "SHL", "SHR", "ROL", "ROR", "INC", "DEC"}:
        return 1

    # Arithmetic / Logic
    if mnemonic in {"ADD", "SUB", "AND", "OR", "XOR", "CMP"}:
        if not item.operands:
            return 1  # e.g. ADD -> ADD B
        first = item.operands[0]
        if first.upper() == "B":
            return 1  # ADD B
        return 2

    if mnemonic in {"LDA", "LDB"}:
        if not item.operands:
            raise AssemblerError(f"Line {item.line_no}: {mnemonic} requires an operand")
        first = item.operands[0].strip()
        if mnemonic == "LDA" and first.upper() == "[B]":
            return 1  # LDA [B]
        return 2

    if mnemonic == "STA":
        if not item.operands:
            raise AssemblerError(f"Line {item.line_no}: STA requires an address or [B]")
        first = item.operands[0].strip()
        if first.upper() == "[B]":
            return 1  # STA [B]
        return 2  # STA addr

    if mnemonic == "STB":
        if not item.operands:
            raise AssemblerError(f"Line {item.line_no}: STB requires an address")
        return 2

    raise AssemblerError(f"Line {item.line_no}: unknown mnemonic '{mnemonic}'")


def assemble(source: str) -> List[int]:
    parsed = _parse_source(source)

    labels: Dict[str, int] = {}
    constants: Dict[str, int] = {}
    address = 0
    max_address = 0

    # Pass 1: Symbol resolution and address calculation
    for item in parsed:
        if item.label is not None:
            if item.label in labels:
                raise AssemblerError(f"Line {item.line_no}: duplicate label '{item.label}'")
            if item.label in constants:
                raise AssemblerError(f"Line {item.line_no}: label '{item.label}' conflicts with constant")
            labels[item.label] = address

        if item.mnemonic == ".EQU":
            if len(item.operands) != 2:
                raise AssemblerError(f"Line {item.line_no}: .EQU requires name and value")
            name = item.operands[0]
            if name in labels or name in constants:
                raise AssemblerError(f"Line {item.line_no}: duplicate symbol '{name}'")
            constants[name] = _resolve_operand(item.operands[1], labels, constants, item.line_no)
            continue

        if item.mnemonic == ".ORG":
            if len(item.operands) != 1:
                raise AssemblerError(f"Line {item.line_no}: .ORG requires one address operand")
            address = _resolve_operand(item.operands[0], labels, constants, item.line_no)
            max_address = max(max_address, address)
            continue

        size = _instruction_size(item)
        address += size
        max_address = max(max_address, address)
        if max_address > 256:
            raise AssemblerError(f"Line {item.line_no}: Program exceeds 256-byte RAM (reached {max_address} bytes)")

    # Pass 2: Bytecode generation
    output: List[int] = [0] * max_address
    address = 0

    def emit(byte_value: int) -> None:
        nonlocal address
        if address >= 256:
            raise AssemblerError("Program exceeds 256-byte RAM")
        if address >= len(output):
            output.extend([0] * (address - len(output) + 1))
        output[address] = byte_value & 0xFF
        address += 1

    for item in parsed:
        if item.mnemonic is None:
            continue

        mnemonic = item.mnemonic

        if mnemonic == ".EQU":
            continue

        if mnemonic == ".ORG":
            address = _resolve_operand(item.operands[0], labels, constants, item.line_no)
            continue

        if mnemonic == "DB":
            for operand in item.operands:
                if (operand.startswith('"') and operand.endswith('"')) or (operand.startswith("'") and operand.endswith("'")):
                    data = _unescape_string(operand)
                    for b in data:
                        emit(b)
                else:
                    emit(_resolve_operand(operand, labels, constants, item.line_no))
            continue

        if mnemonic == "DW":
            for operand in item.operands:
                val = _resolve_operand(operand, labels, constants, item.line_no, max_val=0xFFFF)
                emit(val & 0xFF)
                emit((val >> 8) & 0xFF)
            continue

        if mnemonic in ZERO_OPERAND_OPS:
            if item.operands:
                raise AssemblerError(f"Line {item.line_no}: {mnemonic} takes no operands")
            emit(int(ZERO_OPERAND_OPS[mnemonic]))
            continue

        if mnemonic in BRANCH_OPS:
            if len(item.operands) != 1:
                raise AssemblerError(f"Line {item.line_no}: {mnemonic} requires one address operand")
            emit(int(BRANCH_OPS[mnemonic]))
            emit(_resolve_operand(item.operands[0], labels, constants, item.line_no))
            continue

        if mnemonic == "PUSH":
            if len(item.operands) != 1:
                raise AssemblerError(f"Line {item.line_no}: PUSH requires one operand (A, B, or FLAGS)")
            reg = item.operands[0].upper()
            if reg == "A":
                emit(int(OpCode.PUSH_A))
            elif reg == "B":
                emit(int(OpCode.PUSH_B))
            elif reg in {"FLAGS", "F"}:
                emit(int(OpCode.PUSHF))
            else:
                raise AssemblerError(f"Line {item.line_no}: PUSH supports A, B, or FLAGS")
            continue

        if mnemonic == "POP":
            if len(item.operands) != 1:
                raise AssemblerError(f"Line {item.line_no}: POP requires one operand (A, B, or FLAGS)")
            reg = item.operands[0].upper()
            if reg == "A":
                emit(int(OpCode.POP_A))
            elif reg == "B":
                emit(int(OpCode.POP_B))
            elif reg in {"FLAGS", "F"}:
                emit(int(OpCode.POPF))
            else:
                raise AssemblerError(f"Line {item.line_no}: POP supports A, B, or FLAGS")
            continue

        if mnemonic == "MOV":
            if len(item.operands) != 2:
                raise AssemblerError(f"Line {item.line_no}: MOV requires dst and src registers (e.g. MOV A, B)")
            dst, src = item.operands[0].upper(), item.operands[1].upper()
            if dst == "A" and src == "B":
                emit(int(OpCode.MOV_A_B))
            elif dst == "B" and src == "A":
                emit(int(OpCode.MOV_B_A))
            else:
                raise AssemblerError(f"Line {item.line_no}: unsupported MOV operands {dst}, {src}")
            continue

        if mnemonic == "NOT":
            if item.operands and item.operands[0].upper() != "A":
                raise AssemblerError(f"Line {item.line_no}: NOT only operates on register A")
            emit(int(OpCode.NOT_A))
            continue

        if mnemonic in {"INC", "DEC"}:
            reg = item.operands[0].upper() if item.operands else "A"
            if mnemonic == "INC":
                emit(int(OpCode.INC_A if reg == "A" else OpCode.INC_B))
            else:
                emit(int(OpCode.DEC_A if reg == "A" else OpCode.DEC_B))
            continue

        if mnemonic in {"SHL", "SHR", "ROL", "ROR"}:
            if item.operands and item.operands[0].upper() != "A":
                raise AssemblerError(f"Line {item.line_no}: {mnemonic} only operates on register A")
            table = {
                "SHL": OpCode.SHL_A,
                "SHR": OpCode.SHR_A,
                "ROL": OpCode.ROL_A,
                "ROR": OpCode.ROR_A,
            }
            emit(int(table[mnemonic]))
            continue

        if mnemonic in {"ADD", "SUB", "AND", "OR", "XOR", "CMP"}:
            is_reg_b = not item.operands or (len(item.operands) == 1 and item.operands[0].upper() == "B")
            if is_reg_b:
                table_reg = {
                    "ADD": OpCode.ADD_B,
                    "SUB": OpCode.SUB_B,
                    "AND": OpCode.AND_B,
                    "OR": OpCode.OR_B,
                    "XOR": OpCode.XOR_B,
                    "CMP": OpCode.CMP_B,
                }
                emit(int(table_reg[mnemonic]))
            else:
                table_imm = {
                    "ADD": OpCode.ADD_IMM,
                    "SUB": OpCode.SUB_IMM,
                    "AND": OpCode.AND_IMM,
                    "OR": OpCode.OR_IMM,
                    "XOR": OpCode.XOR_IMM,
                    "CMP": OpCode.CMP_IMM,
                }
                emit(int(table_imm[mnemonic]))
                emit(_resolve_operand(item.operands[0], labels, constants, item.line_no))
            continue

        if mnemonic == "LDA":
            if len(item.operands) != 1:
                raise AssemblerError(f"Line {item.line_no}: LDA requires one operand")
            op = item.operands[0].strip()
            if op.upper() == "[B]":
                emit(int(OpCode.LDA_IND_B))
            elif op.startswith("#"):
                emit(int(OpCode.LDA_IMM))
                emit(_resolve_operand(op, labels, constants, item.line_no))
            elif op.startswith("[") and op.endswith("]"):
                emit(int(OpCode.LDA_ABS))
                emit(_resolve_operand(op, labels, constants, item.line_no))
            elif op in labels:
                emit(int(OpCode.LDA_ABS))
                emit(_resolve_operand(op, labels, constants, item.line_no))
            elif op in constants:
                emit(int(OpCode.LDA_IMM))
                emit(_resolve_operand(op, labels, constants, item.line_no))
            else:
                # Default: bare numbers or addresses without '#' load from memory
                emit(int(OpCode.LDA_ABS))
                emit(_resolve_operand(op, labels, constants, item.line_no))
            continue

        if mnemonic == "LDB":
            if len(item.operands) != 1:
                raise AssemblerError(f"Line {item.line_no}: LDB requires one operand")
            op = item.operands[0].strip()
            if op.startswith("#"):
                emit(int(OpCode.LDB_IMM))
                emit(_resolve_operand(op, labels, constants, item.line_no))
            elif op.startswith("[") and op.endswith("]"):
                emit(int(OpCode.LDB_ABS))
                emit(_resolve_operand(op, labels, constants, item.line_no))
            elif op in labels:
                emit(int(OpCode.LDB_ABS))
                emit(_resolve_operand(op, labels, constants, item.line_no))
            elif op in constants:
                emit(int(OpCode.LDB_IMM))
                emit(_resolve_operand(op, labels, constants, item.line_no))
            else:
                emit(int(OpCode.LDB_ABS))
                emit(_resolve_operand(op, labels, constants, item.line_no))
            continue

        if mnemonic == "STA":
            if len(item.operands) != 1:
                raise AssemblerError(f"Line {item.line_no}: STA requires one address operand")
            op = item.operands[0].strip()
            if op.upper() == "[B]":
                emit(int(OpCode.STA_IND_B))
            else:
                emit(int(OpCode.STA_ABS))
                emit(_resolve_operand(op, labels, constants, item.line_no))
            continue

        if mnemonic == "STB":
            if len(item.operands) != 1:
                raise AssemblerError(f"Line {item.line_no}: STB requires one address operand")
            emit(int(OpCode.STB_ABS))
            emit(_resolve_operand(item.operands[0], labels, constants, item.line_no))
            continue

        raise AssemblerError(f"Line {item.line_no}: unsupported mnemonic '{mnemonic}'")

    return output


def assemble_file(file_path: str) -> List[int]:
    with open(file_path, "r", encoding="utf-8") as source_file:
        return assemble(source_file.read())
