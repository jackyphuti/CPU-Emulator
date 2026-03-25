from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from cpu_emulator import OpCode


class AssemblerError(ValueError):
    pass


@dataclass
class ParsedLine:
    line_no: int
    label: str | None
    mnemonic: str | None
    operands: List[str]


UNARY_OPS = {
    "NOP": OpCode.NOP,
    "ADD": OpCode.ADD_B,
    "SUB": OpCode.SUB_B,
    "HLT": OpCode.HLT,
    "RET": OpCode.RET,
}

SINGLE_OPERAND_OPS = {
    "LDA": OpCode.LDA_IMM,
    "LDB": OpCode.LDB_IMM,
    "STA": OpCode.STA_ABS,
    "JMP": OpCode.JMP_ABS,
    "JZ": OpCode.JZ_ABS,
    "CALL": OpCode.CALL_ABS,
}


def _strip_comment(line: str) -> str:
    semicolon_split = line.split(";", maxsplit=1)[0]
    slash_split = semicolon_split.split("//", maxsplit=1)[0]
    return slash_split.strip()


def _parse_number(token: str) -> int:
    token = token.strip()
    if token.startswith("#"):
        token = token[1:]

    if token.lower().startswith("0x"):
        value = int(token, 16)
    elif token.lower().startswith("0b"):
        value = int(token, 2)
    elif token.lower().endswith("h") and len(token) > 1:
        value = int(token[:-1], 16)
    else:
        value = int(token, 10)

    if not 0 <= value <= 0xFF:
        raise AssemblerError(f"Value out of 8-bit range: {value}")
    return value


def _tokenize(line: str) -> List[str]:
    normalized = line.replace(",", " ")
    return [part for part in normalized.split() if part]


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


def _instruction_size(item: ParsedLine) -> int:
    if item.mnemonic is None:
        return 0

    if item.mnemonic in {".ORG", ".EQU"}:
        return 0

    if item.mnemonic in {"PUSH", "POP"}:
        return 1

    if item.mnemonic in {"ADD", "SUB"}:
        return 1

    if item.mnemonic == "DB":
        if not item.operands:
            raise AssemblerError(f"Line {item.line_no}: DB requires at least one operand")
        return len(item.operands)

    if item.mnemonic in UNARY_OPS:
        return 1

    if item.mnemonic in SINGLE_OPERAND_OPS:
        return 2

    raise AssemblerError(f"Line {item.line_no}: unknown mnemonic '{item.mnemonic}'")


def _resolve_operand(token: str, labels: Dict[str, int], constants: Dict[str, int], line_no: int) -> int:
    if token in constants:
        return constants[token]

    if token in labels:
        return labels[token]

    try:
        return _parse_number(token)
    except ValueError as exc:
        raise AssemblerError(f"Line {line_no}: unknown label or invalid number '{token}'") from exc


def assemble(source: str) -> List[int]:
    parsed = _parse_source(source)

    labels: Dict[str, int] = {}
    constants: Dict[str, int] = {}
    address = 0
    max_address = 0

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
            raise AssemblerError("Program exceeds 256-byte RAM")

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
                emit(_resolve_operand(operand, labels, constants, item.line_no))
            continue

        if mnemonic in {"ADD", "SUB"}:
            if len(item.operands) > 1:
                raise AssemblerError(f"Line {item.line_no}: too many operands for {mnemonic}")
            if item.operands and item.operands[0].upper() != "B":
                raise AssemblerError(f"Line {item.line_no}: {mnemonic} only supports register B")
            emit(int(UNARY_OPS[mnemonic]))
            continue

        if mnemonic == "PUSH":
            if len(item.operands) != 1:
                raise AssemblerError(f"Line {item.line_no}: PUSH requires one register operand")
            reg = item.operands[0].upper()
            if reg == "A":
                emit(int(OpCode.PUSH_A))
            elif reg == "B":
                emit(int(OpCode.PUSH_B))
            else:
                raise AssemblerError(f"Line {item.line_no}: PUSH supports only A or B")
            continue

        if mnemonic == "POP":
            if len(item.operands) != 1:
                raise AssemblerError(f"Line {item.line_no}: POP requires one register operand")
            reg = item.operands[0].upper()
            if reg == "A":
                emit(int(OpCode.POP_A))
            elif reg == "B":
                emit(int(OpCode.POP_B))
            else:
                raise AssemblerError(f"Line {item.line_no}: POP supports only A or B")
            continue

        if mnemonic in UNARY_OPS:
            if item.operands:
                raise AssemblerError(f"Line {item.line_no}: {mnemonic} takes no operands")
            emit(int(UNARY_OPS[mnemonic]))
            continue

        if mnemonic in SINGLE_OPERAND_OPS:
            if len(item.operands) != 1:
                raise AssemblerError(f"Line {item.line_no}: {mnemonic} requires one operand")
            emit(int(SINGLE_OPERAND_OPS[mnemonic]))
            emit(_resolve_operand(item.operands[0], labels, constants, item.line_no))
            continue

        raise AssemblerError(f"Line {item.line_no}: unsupported mnemonic '{mnemonic}'")

    return output


def assemble_file(file_path: str) -> List[int]:
    with open(file_path, "r", encoding="utf-8") as source_file:
        return assemble(source_file.read())
