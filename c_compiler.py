#!/usr/bin/env python3
"""
Mini-C Compiler for 8-bit CPU Emulator.
Compiles a subset of C into 8-bit CPU Assembly.

Supported Features:
- Types: int (8-bit unsigned 0-255), void
- Functions: void main(), int func(...)
- Statements: if / else, while, return, variable declarations, assignments
- Expressions: +, -, &, |, ^, ==, !=, <, <=, >, >=, function calls
- Array indexing: arr[i] (using indirect memory LDA [B] / STA [B])
- Built-ins:
    print_char(c) / putchar(c)  -> writes to MMIO 0xF0
    print_num(n)                -> writes to MMIO 0xF1
    print_hex(h)                -> writes to MMIO 0xF2
    rand()                      -> reads from MMIO 0xFE
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union


# =====================================================================
# Lexer
# =====================================================================

class TokenType(Enum):
    KEYWORD = auto()
    IDENTIFIER = auto()
    NUMBER = auto()
    CHAR_LITERAL = auto()
    STRING_LITERAL = auto()
    OPERATOR = auto()
    DELIMITER = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    col: int


KEYWORDS = {
    "int", "void", "if", "else", "while", "return"
}

OPERATORS = {
    "==", "!=", "<=", ">=", "<", ">", "+", "-", "&", "|", "^", "="
}


class Lexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        length = len(self.source)

        while self.pos < length:
            c = self.source[self.pos]

            # Whitespace
            if c in (" ", "\t", "\r"):
                self.pos += 1
                self.col += 1
                continue
            if c == "\n":
                self.pos += 1
                self.line += 1
                self.col = 1
                continue

            # Comments
            if c == "/" and self.pos + 1 < length:
                next_c = self.source[self.pos + 1]
                if next_c == "/":
                    # Single-line comment
                    while self.pos < length and self.source[self.pos] != "\n":
                        self.pos += 1
                    continue
                elif next_c == "*":
                    # Multi-line comment
                    self.pos += 2
                    while self.pos + 1 < length and not (self.source[self.pos] == "*" and self.source[self.pos + 1] == "/"):
                        if self.source[self.pos] == "\n":
                            self.line += 1
                            self.col = 1
                        else:
                            self.col += 1
                        self.pos += 1
                    self.pos += 2
                    continue

            start_col = self.col

            # Two-character operators
            if self.pos + 1 < length:
                two_char = self.source[self.pos : self.pos + 2]
                if two_char in ("==", "!=", "<=", ">="):
                    self.tokens.append(Token(TokenType.OPERATOR, two_char, self.line, start_col))
                    self.pos += 2
                    self.col += 2
                    continue

            # Single-character operators & delimiters
            if c in "+-&|^=":
                self.tokens.append(Token(TokenType.OPERATOR, c, self.line, start_col))
                self.pos += 1
                self.col += 1
                continue
            if c in "(){}[];,":
                self.tokens.append(Token(TokenType.DELIMITER, c, self.line, start_col))
                self.pos += 1
                self.col += 1
                continue
            if c in "<>":
                self.tokens.append(Token(TokenType.OPERATOR, c, self.line, start_col))
                self.pos += 1
                self.col += 1
                continue

            # Character literal
            if c == "'":
                self.pos += 1
                char_val = self.source[self.pos]
                if char_val == "\\":
                    self.pos += 1
                    esc = self.source[self.pos]
                    esc_map = {"n": 10, "r": 13, "t": 9, "0": 0, "\\": ord("\\"), "'": ord("'")}
                    num_val = esc_map.get(esc, ord(esc))
                else:
                    num_val = ord(char_val)
                self.pos += 1
                if self.pos < length and self.source[self.pos] == "'":
                    self.pos += 1
                self.tokens.append(Token(TokenType.NUMBER, num_val & 0xFF, self.line, start_col))
                self.col += 3
                continue

            # String literal
            if c == '"':
                self.pos += 1
                chars = []
                while self.pos < length and self.source[self.pos] != '"':
                    if self.source[self.pos] == "\\":
                        self.pos += 1
                        esc = self.source[self.pos]
                        esc_map = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "\\": "\\", '"': '"'}
                        chars.append(esc_map.get(esc, esc))
                    else:
                        chars.append(self.source[self.pos])
                    self.pos += 1
                if self.pos < length and self.source[self.pos] == '"':
                    self.pos += 1
                self.tokens.append(Token(TokenType.STRING_LITERAL, "".join(chars), self.line, start_col))
                continue

            # Numbers (Hex, Binary, Decimal)
            if c.isdigit():
                start = self.pos
                if c == "0" and self.pos + 1 < length and self.source[self.pos + 1] in "xX":
                    self.pos += 2
                    while self.pos < length and self.source[self.pos].isalnum():
                        self.pos += 1
                    num_str = self.source[start:self.pos]
                    val = int(num_str, 16)
                elif c == "0" and self.pos + 1 < length and self.source[self.pos + 1] in "bB":
                    self.pos += 2
                    while self.pos < length and self.source[self.pos] in "01":
                        self.pos += 1
                    num_str = self.source[start:self.pos]
                    val = int(num_str, 2)
                else:
                    while self.pos < length and self.source[self.pos].isdigit():
                        self.pos += 1
                    num_str = self.source[start:self.pos]
                    val = int(num_str, 10)

                self.tokens.append(Token(TokenType.NUMBER, val & 0xFF, self.line, start_col))
                self.col += (self.pos - start)
                continue

            # Identifiers and keywords
            if c.isalpha() or c == "_":
                start = self.pos
                while self.pos < length and (self.source[self.pos].isalnum() or self.source[self.pos] == "_"):
                    self.pos += 1
                name = self.source[start:self.pos]
                tok_type = TokenType.KEYWORD if name in KEYWORDS else TokenType.IDENTIFIER
                self.tokens.append(Token(tok_type, name, self.line, start_col))
                self.col += (self.pos - start)
                continue

            raise SyntaxError(f"Unexpected character '{c}' at line {self.line}, col {self.col}")

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return self.tokens


# =====================================================================
# AST Nodes
# =====================================================================

@dataclass
class ASTNode:
    pass

@dataclass
class ProgramNode(ASTNode):
    functions: List[FunctionNode]
    global_vars: List[VarDeclNode] = field(default_factory=list)

@dataclass
class FunctionNode(ASTNode):
    return_type: str
    name: str
    params: List[str]
    body: BlockNode

@dataclass
class BlockNode(ASTNode):
    statements: List[ASTNode]

@dataclass
class VarDeclNode(ASTNode):
    name: str
    init_expr: Optional[ASTNode]
    array_size: Optional[int] = None

@dataclass
class AssignNode(ASTNode):
    name: str
    expr: ASTNode
    index_expr: Optional[ASTNode] = None

@dataclass
class IfNode(ASTNode):
    cond: ASTNode
    then_branch: BlockNode
    else_branch: Optional[BlockNode] = None

@dataclass
class WhileNode(ASTNode):
    cond: ASTNode
    body: BlockNode

@dataclass
class ReturnNode(ASTNode):
    expr: Optional[ASTNode]

@dataclass
class ExprStmtNode(ASTNode):
    expr: ASTNode

@dataclass
class BinaryOpNode(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode

@dataclass
class NumberNode(ASTNode):
    value: int

@dataclass
class VariableNode(ASTNode):
    name: str
    index_expr: Optional[ASTNode] = None

@dataclass
class CallNode(ASTNode):
    name: str
    args: List[ASTNode]


# =====================================================================
# Parser
# =====================================================================

class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, expected_type: Optional[TokenType] = None, expected_val: Any = None) -> Token:
        tok = self.peek()
        if expected_type and tok.type != expected_type:
            raise SyntaxError(f"Line {tok.line}: Expected token type {expected_type}, got {tok.type}")
        if expected_val is not None and tok.value != expected_val:
            raise SyntaxError(f"Line {tok.line}: Expected '{expected_val}', got '{tok.value}'")
        self.pos += 1
        return tok

    def match(self, val: Any) -> bool:
        if self.peek().value == val:
            self.pos += 1
            return True
        return False

    def parse(self) -> ProgramNode:
        functions = []
        global_vars = []

        while self.peek().type != TokenType.EOF:
            # Check for var decl or function
            ret_type = self.consume(TokenType.KEYWORD).value
            name = self.consume(TokenType.IDENTIFIER).value

            if self.match("("):
                # Function
                params = []
                if not self.match(")"):
                    while True:
                        self.consume(TokenType.KEYWORD)  # param type e.g. int
                        pname = self.consume(TokenType.IDENTIFIER).value
                        params.append(pname)
                        if self.match(")"):
                            break
                        self.consume(TokenType.DELIMITER, ",")
                body = self.parse_block()
                functions.append(FunctionNode(ret_type, name, params, body))
            elif self.match("["):
                # Array declaration
                size_tok = self.consume(TokenType.NUMBER)
                self.consume(TokenType.DELIMITER, "]")
                self.consume(TokenType.DELIMITER, ";")
                global_vars.append(VarDeclNode(name, None, array_size=size_tok.value))
            else:
                # Global variable
                init_expr = None
                if self.match("="):
                    init_expr = self.parse_expression()
                self.consume(TokenType.DELIMITER, ";")
                global_vars.append(VarDeclNode(name, init_expr))

        return ProgramNode(functions=functions, global_vars=global_vars)

    def parse_block(self) -> BlockNode:
        self.consume(TokenType.DELIMITER, "{")
        stmts = []
        while not self.match("}"):
            stmts.append(self.parse_statement())
        return BlockNode(stmts)

    def parse_statement(self) -> ASTNode:
        tok = self.peek()

        if tok.type == TokenType.KEYWORD:
            if tok.value == "int":
                self.consume()
                name = self.consume(TokenType.IDENTIFIER).value
                if self.match("["):
                    size_tok = self.consume(TokenType.NUMBER)
                    self.consume(TokenType.DELIMITER, "]")
                    self.consume(TokenType.DELIMITER, ";")
                    return VarDeclNode(name, None, array_size=size_tok.value)
                init_expr = None
                if self.match("="):
                    init_expr = self.parse_expression()
                self.consume(TokenType.DELIMITER, ";")
                return VarDeclNode(name, init_expr)

            if tok.value == "if":
                self.consume()
                self.consume(TokenType.DELIMITER, "(")
                cond = self.parse_expression()
                self.consume(TokenType.DELIMITER, ")")
                then_branch = self.parse_block() if self.peek().value == "{" else BlockNode([self.parse_statement()])
                else_branch = None
                if self.match("else"):
                    else_branch = self.parse_block() if self.peek().value == "{" else BlockNode([self.parse_statement()])
                return IfNode(cond, then_branch, else_branch)

            if tok.value == "while":
                self.consume()
                self.consume(TokenType.DELIMITER, "(")
                cond = self.parse_expression()
                self.consume(TokenType.DELIMITER, ")")
                body = self.parse_block() if self.peek().value == "{" else BlockNode([self.parse_statement()])
                return WhileNode(cond, body)

            if tok.value == "return":
                self.consume()
                expr = None
                if not self.match(";"):
                    expr = self.parse_expression()
                    self.consume(TokenType.DELIMITER, ";")
                return ReturnNode(expr)

        if tok.type == TokenType.IDENTIFIER:
            # Check if assignment: name = ... or name[idx] = ...
            next_tok = self.tokens[self.pos + 1]
            if next_tok.value == "=":
                name = self.consume().value
                self.consume(TokenType.OPERATOR, "=")
                expr = self.parse_expression()
                self.consume(TokenType.DELIMITER, ";")
                return AssignNode(name, expr)
            elif next_tok.value == "[":
                name = self.consume().value
                self.consume(TokenType.DELIMITER, "[")
                idx_expr = self.parse_expression()
                self.consume(TokenType.DELIMITER, "]")
                self.consume(TokenType.OPERATOR, "=")
                expr = self.parse_expression()
                self.consume(TokenType.DELIMITER, ";")
                return AssignNode(name, expr, index_expr=idx_expr)

        # Expression statement (e.g. function call)
        expr = self.parse_expression()
        self.consume(TokenType.DELIMITER, ";")
        return ExprStmtNode(expr)

    def parse_expression(self) -> ASTNode:
        return self.parse_equality()

    def parse_equality(self) -> ASTNode:
        left = self.parse_comparison()
        while self.peek().value in ("==", "!="):
            op = self.consume().value
            right = self.parse_comparison()
            left = BinaryOpNode(op, left, right)
        return left

    def parse_comparison(self) -> ASTNode:
        left = self.parse_additive()
        while self.peek().value in ("<", "<=", ">", ">="):
            op = self.consume().value
            right = self.parse_additive()
            left = BinaryOpNode(op, left, right)
        return left

    def parse_additive(self) -> ASTNode:
        left = self.parse_bitwise()
        while self.peek().value in ("+", "-"):
            op = self.consume().value
            right = self.parse_bitwise()
            left = BinaryOpNode(op, left, right)
        return left

    def parse_bitwise(self) -> ASTNode:
        left = self.parse_primary()
        while self.peek().value in ("&", "|", "^"):
            op = self.consume().value
            right = self.parse_primary()
            left = BinaryOpNode(op, left, right)
        return left

    def parse_primary(self) -> ASTNode:
        tok = self.peek()

        if tok.type == TokenType.NUMBER:
            self.consume()
            return NumberNode(tok.value)

        if tok.type == TokenType.IDENTIFIER:
            name = self.consume().value
            if self.match("("):
                # Call
                args = []
                if not self.match(")"):
                    while True:
                        args.append(self.parse_expression())
                        if self.match(")"):
                            break
                        self.consume(TokenType.DELIMITER, ",")
                return CallNode(name, args)
            elif self.match("["):
                # Array index
                idx_expr = self.parse_expression()
                self.consume(TokenType.DELIMITER, "]")
                return VariableNode(name, index_expr=idx_expr)
            return VariableNode(name)

        if self.match("("):
            expr = self.parse_expression()
            self.consume(TokenType.DELIMITER, ")")
            return expr

        raise SyntaxError(f"Line {tok.line}: Unexpected expression token '{tok.value}'")


# =====================================================================
# Code Generator (Targets 8-bit CPU Assembly)
# =====================================================================

class CodeGenerator:
    def __init__(self) -> None:
        self.lines: List[str] = []
        self.label_counter = 0
        self.var_table: Dict[str, int] = {}
        # Start allocating variables at high RAM address (0xC0..0xEE)
        self.next_var_addr = 0xC0

    def new_label(self, prefix: str = "L") -> str:
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def emit(self, instruction: str, comment: str = "") -> None:
        if comment:
            self.lines.append(f"    {instruction:<16} ; {comment}")
        else:
            self.lines.append(f"    {instruction}")

    def emit_label(self, label: str) -> None:
        self.lines.append(f"{label}:")

    def allocate_var(self, name: str, size: int = 1) -> int:
        if name in self.var_table:
            return self.var_table[name]
        addr = self.next_var_addr
        self.var_table[name] = addr
        self.next_var_addr += size
        if self.next_var_addr >= 0xF0:
            raise MemoryError("Exceeded variable memory area in RAM (max 0xEF)")
        return addr

    def compile(self, ast: ProgramNode) -> str:
        self.lines.append("; Generated by Mini-C Compiler for 8-bit CPU")
        self.lines.append(".ORG 0x00")
        self.lines.append("    JMP main_entry\n")

        # Global variables
        for gvar in ast.global_vars:
            size = gvar.array_size if gvar.array_size else 1
            addr = self.allocate_var(gvar.name, size=size)
            if gvar.init_expr and isinstance(gvar.init_expr, NumberNode):
                self.lines.append(f"; Global {gvar.name} @ 0x{addr:02X} = {gvar.init_expr.value}")

        # Functions
        for func in ast.functions:
            if func.name == "main":
                self.emit_label("main_entry")
            else:
                self.emit_label(f"func_{func.name}")

            for p in func.params:
                self.allocate_var(p)

            self.gen_block(func.body)

            if func.name == "main":
                self.emit("HLT", "end of program")
            else:
                self.emit("RET")
            self.lines.append("")

        return "\n".join(self.lines)

    def gen_block(self, block: BlockNode) -> None:
        for stmt in block.statements:
            self.gen_statement(stmt)

    def gen_statement(self, stmt: ASTNode) -> None:
        if isinstance(stmt, VarDeclNode):
            addr = self.allocate_var(stmt.name, size=stmt.array_size if stmt.array_size else 1)
            if stmt.init_expr:
                self.gen_expression(stmt.init_expr)
                self.emit(f"STA 0x{addr:02X}", f"{stmt.name} = init")

        elif isinstance(stmt, AssignNode):
            if stmt.index_expr:
                # arr[i] = expr
                # 1. evaluate RHS expr -> push
                self.gen_expression(stmt.expr)
                self.emit("PUSH A", "save RHS value")
                # 2. evaluate index
                self.gen_expression(stmt.index_expr)
                base = self.allocate_var(stmt.name)
                self.emit(f"ADD #{base}", f"offset + &{stmt.name}")
                self.emit("MOV B, A", "address into B")
                self.emit("POP A", "restore RHS value")
                self.emit("STA [B]", f"{stmt.name}[i] = A")
            else:
                addr = self.allocate_var(stmt.name)
                self.gen_expression(stmt.expr)
                self.emit(f"STA 0x{addr:02X}", f"{stmt.name} = A")

        elif isinstance(stmt, IfNode):
            else_label = self.new_label("else")
            end_label = self.new_label("endif")

            self.gen_condition(stmt.cond, false_label=else_label if stmt.else_branch else end_label)
            self.gen_block(stmt.then_branch)

            if stmt.else_branch:
                self.emit(f"JMP {end_label}")
                self.emit_label(else_label)
                self.gen_block(stmt.else_branch)

            self.emit_label(end_label)

        elif isinstance(stmt, WhileNode):
            loop_label = self.new_label("while_start")
            end_label = self.new_label("while_end")

            self.emit_label(loop_label)
            self.gen_condition(stmt.cond, false_label=end_label)
            self.gen_block(stmt.body)
            self.emit(f"JMP {loop_label}")
            self.emit_label(end_label)

        elif isinstance(stmt, ReturnNode):
            if stmt.expr:
                self.gen_expression(stmt.expr)
            self.emit("RET")

        elif isinstance(stmt, ExprStmtNode):
            self.gen_expression(stmt.expr)

    def gen_condition(self, cond: ASTNode, false_label: str) -> None:
        if isinstance(cond, BinaryOpNode) and cond.op in ("==", "!=", "<", "<=", ">", ">="):
            # Evaluate left into A, push, evaluate right into A
            self.gen_expression(cond.left)
            self.emit("PUSH A")
            self.gen_expression(cond.right)
            self.emit("MOV B, A", "B = right")
            self.emit("POP A", "A = left")
            self.emit("CMP B", "compare left and right")

            # Jump to false_label if condition is NOT met
            if cond.op == "==":
                self.emit(f"JNZ {false_label}", "jump if !=")
            elif cond.op == "!=":
                self.emit(f"JZ {false_label}", "jump if ==")
            elif cond.op == "<":
                # A < B sets Carry flag
                self.emit(f"JNC {false_label}", "jump if not <")
            elif cond.op == ">=":
                self.emit(f"JC {false_label}", "jump if <")
            elif cond.op == ">":
                # A > B means not (A <= B)
                # If equal or carry, jump to false
                self.emit(f"JC {false_label}")
                self.emit(f"JZ {false_label}")
            elif cond.op == "<=":
                # If greater (not carry and not zero), jump to false
                pass_label = self.new_label("lte_true")
                self.emit(f"JC {pass_label}")
                self.emit(f"JZ {pass_label}")
                self.emit(f"JMP {false_label}")
                self.emit_label(pass_label)
        else:
            # Simple truthiness (non-zero)
            self.gen_expression(cond)
            self.emit("CMP #0")
            self.emit(f"JZ {false_label}", "jump if zero")

    def gen_expression(self, expr: ASTNode) -> None:
        if isinstance(expr, NumberNode):
            self.emit(f"LDA #{expr.value}")

        elif isinstance(expr, VariableNode):
            base = self.allocate_var(expr.name)
            if expr.index_expr:
                # Array index load: arr[i]
                self.gen_expression(expr.index_expr)
                self.emit(f"ADD #{base}")
                self.emit("MOV B, A")
                self.emit("LDA [B]", f"load {expr.name}[i]")
            else:
                self.emit(f"LDA 0x{base:02X}", f"load {expr.name}")

        elif isinstance(expr, BinaryOpNode):
            # Arithmetic & Bitwise
            self.gen_expression(expr.left)
            self.emit("PUSH A")
            self.gen_expression(expr.right)
            self.emit("MOV B, A")
            self.emit("POP A")

            if expr.op == "+":
                self.emit("ADD B")
            elif expr.op == "-":
                self.emit("SUB B")
            elif expr.op == "&":
                self.emit("AND B")
            elif expr.op == "|":
                self.emit("OR B")
            elif expr.op == "^":
                self.emit("XOR B")

        elif isinstance(expr, CallNode):
            # Built-ins
            if expr.name in ("print_char", "putchar"):
                self.gen_expression(expr.args[0])
                self.emit("STA 0xF0", "MMIO char output")
            elif expr.name == "print_num":
                self.gen_expression(expr.args[0])
                self.emit("STA 0xF1", "MMIO num output")
            elif expr.name == "print_hex":
                self.gen_expression(expr.args[0])
                self.emit("STA 0xF2", "MMIO hex output")
            elif expr.name == "rand":
                self.emit("LDA 0xFE", "MMIO random byte")
            else:
                # Custom function call
                for arg in expr.args:
                    self.gen_expression(arg)
                    # For simple single/few-arg functions
                self.emit(f"CALL func_{expr.name}")


def compile_c(source: str) -> str:
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    codegen = CodeGenerator()
    return codegen.compile(ast)


def main() -> None:
    arg_parser = argparse.ArgumentParser(description="Mini-C Compiler for 8-bit CPU Emulator")
    arg_parser.add_argument("input", help="C source code file (.c)")
    arg_parser.add_argument("-o", "--output", help="Output assembly file (.asm)")
    arg_parser.add_argument("--run", action="store_true", help="Assemble and execute immediately in CPU emulator")
    args = arg_parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        c_code = f.read()

    asm_code = compile_c(c_code)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(asm_code)
        print(f"Assembly written to {args.output}")
    else:
        print(asm_code)

    if args.run:
        from assembler import assemble
        from cpu_emulator import CPU8Bit

        bin_data = assemble(asm_code)
        cpu = CPU8Bit()
        cpu.load_program(bin_data)
        print("\n--- Running Program in 8-bit CPU Emulator ---")
        cpu.run(debug=False)
        print(f"\nExecution finished in {cpu.cycles} cycles.")
        if cpu.io_output:
            print("Console Output:", "".join(cpu.io_output))


if __name__ == "__main__":
    main()
