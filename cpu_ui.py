from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox

from assembler import AssemblerError, assemble
from cpu_emulator import CPU8Bit, FLAG_C, FLAG_N, FLAG_Z


DEFAULT_ASM = """; Demo program using stack, constants, and relocation
.EQU OUT_ADDR 0x0F
.ORG 0x00
start:
    LDA #7
    LDB #5
    CALL add_numbers
    STA OUT_ADDR
    HLT

add_numbers:
    PUSH B
    POP B
    ADD B
    RET
"""


class EmulatorUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("8-bit CPU Emulator")
        self.root.geometry("1440x900")
        self.root.configure(bg="#0A0D14")

        self.cpu = CPU8Bit()
        self.running = False
        self.breakpoints: set[int] = set()
        self.watch_addresses: set[int] = set()
        self.run_to_address: int | None = None
        self.trace_lines: list[str] = []
        self.trace_limit = 300
        self.phase_fetch_pc: int | None = None
        self.disasm_line_addresses: list[int] = []
        self.conditional_breakpoint_raw: str | None = None
        self.conditional_breakpoint_rule: tuple[str, str, int] | None = None

        self._build_layout()
        self._load_default_program()

    def _build_layout(self) -> None:
        title = tk.Label(
            self.root,
            text="8-bit CPU Emulator",
            bg="#0A0D14",
            fg="#E4E9F7",
            font=("Consolas", 20, "bold"),
        )
        title.pack(pady=(14, 10))

        main = tk.Frame(self.root, bg="#0A0D14")
        main.pack(fill="both", expand=True, padx=16, pady=8)

        left_col = self._build_register_panel(main)
        left_col.pack(side="left", fill="both", padx=(0, 12), pady=4)

        center_col = self._build_control_panel(main)
        center_col.pack(side="left", fill="both", padx=12, pady=4)

        right_col = self._build_memory_and_debug_panel(main)
        right_col.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=4)

        bottom = self._build_source_panel(self.root)
        bottom.pack(fill="x", padx=16, pady=(6, 14))

    def _card_frame(self, parent: tk.Widget, title_text: str, width: int = 320, height: int = 360) -> tk.Frame:
        card = tk.Frame(parent, bg="#121826", bd=1, relief="solid", width=width, height=height)
        card.pack_propagate(False)

        title = tk.Label(
            card,
            text=title_text,
            bg="#121826",
            fg="#D6DDF0",
            font=("Consolas", 14, "bold"),
        )
        title.pack(pady=(12, 10))
        return card

    def _build_register_panel(self, parent: tk.Widget) -> tk.Frame:
        card = self._card_frame(parent, "REGISTERS", width=300, height=620)

        self.pc_var = tk.StringVar(value="PC: 0x00")
        self.sp_var = tk.StringVar(value="SP: 0xFF")
        self.a_var = tk.StringVar(value="A: 0x00")
        self.b_var = tk.StringVar(value="B: 0x00")
        self.ir_var = tk.StringVar(value="IR: --")
        self.flags_var = tk.StringVar(value="FLAGS [Z C N]: 0 0 0")
        self.cycle_var = tk.StringVar(value="Cycle: 0")
        self.call_depth_var = tk.StringVar(value="Call Depth: 0")
        self.stack_depth_var = tk.StringVar(value="Stack Depth: 0")

        for variable in [
            self.pc_var,
            self.sp_var,
            self.a_var,
            self.b_var,
            self.ir_var,
            self.flags_var,
            self.cycle_var,
            self.call_depth_var,
            self.stack_depth_var,
        ]:
            lbl = tk.Label(
                card,
                textvariable=variable,
                bg="#0E1320",
                fg="#F1F5FF",
                font=("Consolas", 12, "bold"),
                padx=10,
                pady=7,
                anchor="w",
                width=24,
            )
            lbl.pack(pady=4, padx=14)

        meter_title = tk.Label(
            card,
            text="CALL DEPTH METER",
            bg="#121826",
            fg="#A9BCDD",
            font=("Consolas", 10, "bold"),
        )
        meter_title.pack(pady=(10, 4))

        self.call_depth_canvas = tk.Canvas(card, width=240, height=20, bg="#0E1320", highlightthickness=0)
        self.call_depth_canvas.pack(pady=(0, 8))
        self.call_depth_canvas.create_rectangle(0, 0, 240, 20, fill="#24314A", width=0)
        self.call_depth_fill = self.call_depth_canvas.create_rectangle(0, 0, 0, 20, fill="#55D6BE", width=0)
        return card

    def _build_control_panel(self, parent: tk.Widget) -> tk.Frame:
        card = self._card_frame(parent, "CONTROL UNIT", width=380, height=620)

        button_specs = [
            ("FETCH", self.on_fetch),
            ("DECODE", self.on_decode),
            ("EXECUTE", self.on_execute),
            ("STEP", self.on_step),
            ("RUN", self.on_run),
            ("RUN TO ADDRESS", self.on_run_to_address),
            ("RESET", self.on_reset),
            ("ASSEMBLE + LOAD", self.on_assemble_load),
        ]

        for label, callback in button_specs:
            btn = tk.Button(
                card,
                text=label,
                command=callback,
                bg="#182136",
                fg="#EAF1FF",
                activebackground="#253654",
                activeforeground="#FFFFFF",
                font=("Consolas", 11, "bold"),
                width=24,
                relief="flat",
                pady=6,
            )
            btn.pack(pady=4)

        debug_frame = tk.Frame(card, bg="#121826")
        debug_frame.pack(fill="x", padx=14, pady=(8, 4))

        tk.Label(debug_frame, text="Breakpoint Addr (hex/dec)", bg="#121826", fg="#B8C9E8", font=("Consolas", 10, "bold")).pack(anchor="w")
        self.breakpoint_entry = tk.Entry(debug_frame, bg="#0E1320", fg="#EAF1FF", insertbackground="#FFFFFF", font=("Consolas", 10), relief="flat")
        self.breakpoint_entry.pack(fill="x", pady=(4, 6))
        bp_btn_row = tk.Frame(debug_frame, bg="#121826")
        bp_btn_row.pack(fill="x")
        tk.Button(bp_btn_row, text="ADD BP", command=self.on_add_breakpoint, bg="#24324D", fg="#EAF1FF", font=("Consolas", 10, "bold"), relief="flat").pack(side="left", padx=(0, 6))
        tk.Button(bp_btn_row, text="DEL BP", command=self.on_remove_breakpoint, bg="#24324D", fg="#EAF1FF", font=("Consolas", 10, "bold"), relief="flat").pack(side="left", padx=(0, 6))
        tk.Button(bp_btn_row, text="CLEAR", command=self.on_clear_breakpoints, bg="#24324D", fg="#EAF1FF", font=("Consolas", 10, "bold"), relief="flat").pack(side="left")

        tk.Label(debug_frame, text="Conditional Breakpoint", bg="#121826", fg="#B8C9E8", font=("Consolas", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.cond_bp_entry = tk.Entry(debug_frame, bg="#0E1320", fg="#EAF1FF", insertbackground="#FFFFFF", font=("Consolas", 10), relief="flat")
        self.cond_bp_entry.pack(fill="x", pady=(4, 6))
        cond_btn_row = tk.Frame(debug_frame, bg="#121826")
        cond_btn_row.pack(fill="x")
        tk.Button(cond_btn_row, text="SET", command=self.on_set_conditional_breakpoint, bg="#24324D", fg="#EAF1FF", font=("Consolas", 10, "bold"), relief="flat").pack(side="left", padx=(0, 6))
        tk.Button(cond_btn_row, text="CLEAR", command=self.on_clear_conditional_breakpoint, bg="#24324D", fg="#EAF1FF", font=("Consolas", 10, "bold"), relief="flat").pack(side="left")

        tk.Label(debug_frame, text="Run-To Addr (hex/dec)", bg="#121826", fg="#B8C9E8", font=("Consolas", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.run_to_entry = tk.Entry(debug_frame, bg="#0E1320", fg="#EAF1FF", insertbackground="#FFFFFF", font=("Consolas", 10), relief="flat")
        self.run_to_entry.pack(fill="x", pady=(4, 0))

        self.breakpoint_list_var = tk.StringVar(value="Breakpoints: (none)")
        tk.Label(card, textvariable=self.breakpoint_list_var, bg="#121826", fg="#8FA7CF", font=("Consolas", 10), wraplength=340, justify="left").pack(padx=16, pady=(4, 0), anchor="w")

        self.cond_bp_var = tk.StringVar(value="Conditional BP: (none)")
        tk.Label(card, textvariable=self.cond_bp_var, bg="#121826", fg="#8FA7CF", font=("Consolas", 10), wraplength=340, justify="left").pack(padx=16, pady=(4, 0), anchor="w")

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(
            card,
            textvariable=self.status_var,
            bg="#121826",
            fg="#7FD7B9",
            font=("Consolas", 11, "bold"),
            wraplength=340,
            justify="left",
        )
        self.status_label.pack(padx=16, pady=(10, 0), anchor="w")
        return card

    def _build_memory_and_debug_panel(self, parent: tk.Widget) -> tk.Frame:
        card = self._card_frame(parent, "RAM + DEBUG VIEW", width=730, height=620)

        self.ram_text = tk.Text(
            card,
            height=11,
            width=84,
            bg="#0A101C",
            fg="#DCE6FF",
            insertbackground="#FFFFFF",
            font=("Consolas", 11),
            relief="flat",
            bd=0,
            padx=10,
            pady=10,
        )
        self.ram_text.pack(padx=12, pady=(8, 6), fill="x")
        self.ram_text.config(state="disabled")

        lower = tk.Frame(card, bg="#121826")
        lower.pack(fill="both", expand=True, padx=12, pady=(2, 10))

        stack_watch_frame = tk.Frame(lower, bg="#121826")
        stack_watch_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))

        tk.Label(stack_watch_frame, text="STACK WINDOW", bg="#121826", fg="#D6DDF0", font=("Consolas", 10, "bold")).pack(anchor="w")
        self.stack_text = tk.Text(stack_watch_frame, height=8, bg="#0A101C", fg="#DCE6FF", font=("Consolas", 10), relief="flat", bd=0, padx=8, pady=8)
        self.stack_text.pack(fill="both", expand=True, pady=(4, 6))
        self.stack_text.config(state="disabled")

        tk.Label(stack_watch_frame, text="WATCH WINDOW", bg="#121826", fg="#D6DDF0", font=("Consolas", 10, "bold")).pack(anchor="w")
        watch_ctrl = tk.Frame(stack_watch_frame, bg="#121826")
        watch_ctrl.pack(fill="x", pady=(4, 4))
        self.watch_entry = tk.Entry(watch_ctrl, bg="#0E1320", fg="#EAF1FF", insertbackground="#FFFFFF", font=("Consolas", 10), relief="flat")
        self.watch_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(watch_ctrl, text="+", command=self.on_add_watch, bg="#24324D", fg="#EAF1FF", font=("Consolas", 10, "bold"), relief="flat", width=3).pack(side="left", padx=(0, 4))
        tk.Button(watch_ctrl, text="-", command=self.on_remove_watch, bg="#24324D", fg="#EAF1FF", font=("Consolas", 10, "bold"), relief="flat", width=3).pack(side="left", padx=(0, 4))
        tk.Button(watch_ctrl, text="C", command=self.on_clear_watch, bg="#24324D", fg="#EAF1FF", font=("Consolas", 10, "bold"), relief="flat", width=3).pack(side="left")

        self.watch_text = tk.Text(stack_watch_frame, height=5, bg="#0A101C", fg="#BEE8FF", font=("Consolas", 10), relief="flat", bd=0, padx=8, pady=8)
        self.watch_text.pack(fill="both", expand=True)
        self.watch_text.config(state="disabled")

        trace_frame = tk.Frame(lower, bg="#121826")
        trace_frame.pack(side="left", fill="both", expand=True, padx=(4, 4))
        tk.Label(trace_frame, text="INSTRUCTION TRACE", bg="#121826", fg="#D6DDF0", font=("Consolas", 10, "bold")).pack(anchor="w")
        self.trace_text = tk.Text(trace_frame, height=16, bg="#0A101C", fg="#EEDDA8", font=("Consolas", 10), relief="flat", bd=0, padx=8, pady=8)
        self.trace_text.pack(fill="both", expand=True, pady=(4, 0))
        self.trace_text.config(state="disabled")

        disasm_frame = tk.Frame(lower, bg="#121826")
        disasm_frame.pack(side="left", fill="both", expand=True, padx=(4, 0))
        tk.Label(disasm_frame, text="LIVE DISASSEMBLY", bg="#121826", fg="#D6DDF0", font=("Consolas", 10, "bold")).pack(anchor="w")
        tk.Label(disasm_frame, text="Double-click line to toggle breakpoint", bg="#121826", fg="#8FA7CF", font=("Consolas", 9)).pack(anchor="w")
        self.disasm_text = tk.Text(disasm_frame, height=16, bg="#0A101C", fg="#BDE4A8", font=("Consolas", 10), relief="flat", bd=0, padx=8, pady=8)
        self.disasm_text.pack(fill="both", expand=True, pady=(4, 0))
        self.disasm_text.config(state="disabled")
        self.disasm_text.bind("<Double-Button-1>", self.on_toggle_breakpoint_from_disasm)
        return card

    def _build_source_panel(self, parent: tk.Widget) -> tk.Frame:
        frame = tk.Frame(parent, bg="#0A0D14")
        tk.Label(frame, text="Assembly Source", bg="#0A0D14", fg="#D6DDF0", font=("Consolas", 13, "bold")).pack(anchor="w")
        self.source_text = tk.Text(
            frame,
            height=10,
            bg="#0A101C",
            fg="#E6EEFF",
            insertbackground="#FFFFFF",
            font=("Consolas", 11),
            relief="flat",
            bd=0,
            padx=10,
            pady=10,
        )
        self.source_text.pack(fill="x", pady=(6, 0))
        return frame

    def _load_default_program(self) -> None:
        self.source_text.delete("1.0", tk.END)
        self.source_text.insert("1.0", DEFAULT_ASM)
        self.on_assemble_load()

    def _parse_address(self, text: str) -> int:
        token = text.strip()
        if not token:
            raise ValueError("Address is empty")
        value = int(token, 16) if token.lower().startswith("0x") else int(token, 10)
        if not 0 <= value <= 0xFF:
            raise ValueError("Address must be in range 0-255")
        return value

    def _set_status(self, message: str, is_error: bool = False) -> None:
        self.status_var.set(message)
        self.status_label.configure(fg="#FF8A80" if is_error else "#7FD7B9")

    def _record_trace(self, address: int) -> None:
        cycle_idx = max(0, self.cpu.cycles - 1)
        text = self.cpu.decode_instruction_at(self.cpu.ram, address)
        self.trace_lines.append(f"C{cycle_idx:03d} @0x{address:02X}: {text}")
        if len(self.trace_lines) > self.trace_limit:
            self.trace_lines = self.trace_lines[-self.trace_limit :]

    def _execute_one_cycle_with_trace(self) -> None:
        instruction_addr = self.cpu.pc
        self.cpu.step_cycle(debug=False)
        self._record_trace(instruction_addr)

    def _parse_conditional_breakpoint(self, raw: str) -> tuple[str, str, int]:
        pattern = r"^\s*(A|B|PC|SP|CYCLE|Z|C|N|CALL_DEPTH|STACK_DEPTH)\s*(==|!=|<=|>=|<|>)\s*(0x[0-9A-Fa-f]+|\d+)\s*$"
        match = re.match(pattern, raw)
        if not match:
            raise ValueError("Condition format: FIELD OP VALUE, e.g. A==0x0C or CYCLE>=10")
        field, op, value_text = match.groups()
        value = int(value_text, 16) if value_text.lower().startswith("0x") else int(value_text, 10)
        return field, op, value

    def _conditional_field_value(self, field: str) -> int:
        if field == "A":
            return self.cpu.a
        if field == "B":
            return self.cpu.b
        if field == "PC":
            return self.cpu.pc
        if field == "SP":
            return self.cpu.sp
        if field == "CYCLE":
            return self.cpu.cycles
        if field == "Z":
            return int(self.cpu.get_flag(FLAG_Z))
        if field == "C":
            return int(self.cpu.get_flag(FLAG_C))
        if field == "N":
            return int(self.cpu.get_flag(FLAG_N))
        if field == "CALL_DEPTH":
            return self.cpu.call_depth
        if field == "STACK_DEPTH":
            return self.cpu.stack_depth
        raise ValueError(f"Unsupported field: {field}")

    def _conditional_breakpoint_hit(self) -> bool:
        if self.conditional_breakpoint_rule is None:
            return False
        field, op, expected = self.conditional_breakpoint_rule
        current = self._conditional_field_value(field)
        if op == "==":
            return current == expected
        if op == "!=":
            return current != expected
        if op == "<":
            return current < expected
        if op == "<=":
            return current <= expected
        if op == ">":
            return current > expected
        if op == ">=":
            return current >= expected
        return False

    def _build_disassembly_lines(self) -> tuple[list[str], list[int]]:
        lines: list[str] = []
        addresses: list[int] = []
        start = (self.cpu.pc - 8) & 0xFF
        addr = start
        visited = set()

        for _ in range(26):
            if addr in visited:
                break
            visited.add(addr)
            addresses.append(addr)
            marker_parts = []
            if addr == self.cpu.pc:
                marker_parts.append("PC")
            if addr in self.breakpoints:
                marker_parts.append("BP")
            marker = "/".join(marker_parts) if marker_parts else "--"
            text = self.cpu.decode_instruction_at(self.cpu.ram, addr)
            lines.append(f"{marker:>5} 0x{addr:02X}: {text}")
            size = CPU8Bit.opcode_size(self.cpu.ram[addr])
            addr = (addr + max(1, size)) & 0xFF
        return lines, addresses

    def refresh_ui(self) -> None:
        self.pc_var.set(f"PC: 0x{self.cpu.pc:02X}")
        self.sp_var.set(f"SP: 0x{self.cpu.sp:02X}")
        self.a_var.set(f"A: 0x{self.cpu.a:02X}")
        self.b_var.set(f"B: 0x{self.cpu.b:02X}")
        self.ir_var.set("IR: --" if self.cpu.ir is None else f"IR: 0x{self.cpu.ir:02X}")
        self.flags_var.set(f"FLAGS [Z C N]: {int(self.cpu.get_flag(FLAG_Z))} {int(self.cpu.get_flag(FLAG_C))} {int(self.cpu.get_flag(FLAG_N))}")
        self.cycle_var.set(f"Cycle: {self.cpu.cycles}")
        self.call_depth_var.set(f"Call Depth: {self.cpu.call_depth}")
        self.stack_depth_var.set(f"Stack Depth: {self.cpu.stack_depth}")

        depth_ratio = min(1.0, self.cpu.call_depth / 16) if self.cpu.call_depth > 0 else 0.0
        self.call_depth_canvas.coords(self.call_depth_fill, 0, 0, int(240 * depth_ratio), 20)

        bp_text = " ".join(f"0x{addr:02X}" for addr in sorted(self.breakpoints))
        self.breakpoint_list_var.set(f"Breakpoints: {bp_text if bp_text else '(none)'}")
        self.cond_bp_var.set(f"Conditional BP: {self.conditional_breakpoint_raw if self.conditional_breakpoint_raw else '(none)'}")

        rows = []
        for base in range(0, 256, 16):
            row_values = " ".join(f"{value:02X}" for value in self.cpu.ram[base : base + 16])
            rows.append(f"{base:02X}: {row_values}")
        self.ram_text.config(state="normal")
        self.ram_text.delete("1.0", tk.END)
        self.ram_text.insert("1.0", "\n".join(rows))
        self.ram_text.config(state="disabled")

        stack_lines = [f"SP=0x{self.cpu.sp:02X} | depth={self.cpu.stack_depth}"]
        max_entries = min(self.cpu.stack_depth, 16)
        for index in range(max_entries):
            addr = (self.cpu.sp + 1 + index) & 0xFF
            marker = "<- top" if index == 0 else ""
            stack_lines.append(f"[{index:02d}] 0x{addr:02X}: 0x{self.cpu.ram[addr]:02X} {marker}".rstrip())
        if max_entries == 0:
            stack_lines.append("(stack empty)")
        self.stack_text.config(state="normal")
        self.stack_text.delete("1.0", tk.END)
        self.stack_text.insert("1.0", "\n".join(stack_lines))
        self.stack_text.config(state="disabled")

        watch_lines = []
        for addr in sorted(self.watch_addresses):
            watch_lines.append(f"0x{addr:02X}: 0x{self.cpu.ram[addr]:02X} ({self.cpu.ram[addr]})")
        if not watch_lines:
            watch_lines.append("(no watches)")
        self.watch_text.config(state="normal")
        self.watch_text.delete("1.0", tk.END)
        self.watch_text.insert("1.0", "\n".join(watch_lines))
        self.watch_text.config(state="disabled")

        self.trace_text.config(state="normal")
        self.trace_text.delete("1.0", tk.END)
        self.trace_text.insert("1.0", "\n".join(self.trace_lines))
        self.trace_text.config(state="disabled")
        self.trace_text.see(tk.END)

        disasm_lines, disasm_addrs = self._build_disassembly_lines()
        self.disasm_line_addresses = disasm_addrs
        self.disasm_text.config(state="normal")
        self.disasm_text.delete("1.0", tk.END)
        self.disasm_text.insert("1.0", "\n".join(disasm_lines))
        self.disasm_text.config(state="disabled")

    def on_assemble_load(self) -> None:
        try:
            program = assemble(self.source_text.get("1.0", tk.END))
            self.cpu.load_program(program)
            self.running = False
            self.run_to_address = None
            self.phase_fetch_pc = None
            self.trace_lines = []
            self._set_status(f"Program assembled and loaded ({len(program)} bytes).")
            self.refresh_ui()
        except AssemblerError as exc:
            self._set_status(str(exc), is_error=True)
        except Exception as exc:
            self._set_status(f"Load failed: {exc}", is_error=True)

    def on_reset(self) -> None:
        self.running = False
        self.cpu.reset()
        self.run_to_address = None
        self.phase_fetch_pc = None
        self.trace_lines = []
        self._set_status("CPU reset. RAM cleared.")
        self.refresh_ui()

    def on_fetch(self) -> None:
        try:
            self.phase_fetch_pc = self.cpu.pc
            opcode = self.cpu.fetch_phase()
            self._set_status(f"Fetched opcode 0x{opcode:02X}")
            self.refresh_ui()
        except Exception as exc:
            self._set_status(str(exc), is_error=True)

    def on_decode(self) -> None:
        try:
            mnemonic = self.cpu.decode_phase()
            if self.phase_fetch_pc is not None:
                mnemonic = self.cpu.decode_instruction_at(self.cpu.ram, self.phase_fetch_pc)
            self._set_status(f"Decoded: {mnemonic}")
            self.refresh_ui()
        except Exception as exc:
            self._set_status(str(exc), is_error=True)

    def on_execute(self) -> None:
        try:
            executed_addr = self.phase_fetch_pc if self.phase_fetch_pc is not None else self.cpu.pc
            opcode = self.cpu.execute_phase()
            self._record_trace(executed_addr)
            self.phase_fetch_pc = None
            self._set_status(f"Executed opcode 0x{opcode:02X}")
            self.refresh_ui()
        except Exception as exc:
            self._set_status(str(exc), is_error=True)

    def on_step(self) -> None:
        try:
            self.phase_fetch_pc = None
            addr = self.cpu.pc
            opcode = self.cpu.step_cycle(debug=False)
            self._record_trace(addr)
            self._set_status(f"Stepped opcode 0x{opcode:02X}{'. CPU halted.' if self.cpu.halted else ''}")
            self.refresh_ui()
        except Exception as exc:
            self._set_status(str(exc), is_error=True)

    def on_add_breakpoint(self) -> None:
        try:
            addr = self._parse_address(self.breakpoint_entry.get())
            self.breakpoints.add(addr)
            self._set_status(f"Breakpoint added at 0x{addr:02X}")
            self.refresh_ui()
        except Exception as exc:
            self._set_status(f"Add BP failed: {exc}", is_error=True)

    def on_remove_breakpoint(self) -> None:
        try:
            addr = self._parse_address(self.breakpoint_entry.get())
            if addr in self.breakpoints:
                self.breakpoints.remove(addr)
                self._set_status(f"Breakpoint removed at 0x{addr:02X}")
            else:
                self._set_status(f"No breakpoint at 0x{addr:02X}", is_error=True)
            self.refresh_ui()
        except Exception as exc:
            self._set_status(f"Remove BP failed: {exc}", is_error=True)

    def on_clear_breakpoints(self) -> None:
        self.breakpoints.clear()
        self._set_status("All breakpoints cleared.")
        self.refresh_ui()

    def on_set_conditional_breakpoint(self) -> None:
        try:
            raw = self.cond_bp_entry.get().strip()
            if not raw:
                raise ValueError("Condition is empty")
            self.conditional_breakpoint_rule = self._parse_conditional_breakpoint(raw)
            self.conditional_breakpoint_raw = raw
            self._set_status(f"Conditional breakpoint set: {raw}")
            self.refresh_ui()
        except Exception as exc:
            self._set_status(f"Conditional BP error: {exc}", is_error=True)

    def on_clear_conditional_breakpoint(self) -> None:
        self.conditional_breakpoint_rule = None
        self.conditional_breakpoint_raw = None
        self._set_status("Conditional breakpoint cleared.")
        self.refresh_ui()

    def on_run_to_address(self) -> None:
        try:
            target = self._parse_address(self.run_to_entry.get())
            self.run_to_address = target
            if self.cpu.pc == target:
                self._set_status(f"Already at run-to address 0x{target:02X}")
                self.refresh_ui()
                return
            self.running = True
            self._set_status(f"Running to 0x{target:02X}...")
            self._run_loop_tick()
        except Exception as exc:
            self._set_status(f"Run-to failed: {exc}", is_error=True)

    def on_add_watch(self) -> None:
        try:
            addr = self._parse_address(self.watch_entry.get())
            self.watch_addresses.add(addr)
            self._set_status(f"Watch added at 0x{addr:02X}")
            self.refresh_ui()
        except Exception as exc:
            self._set_status(f"Add watch failed: {exc}", is_error=True)

    def on_remove_watch(self) -> None:
        try:
            addr = self._parse_address(self.watch_entry.get())
            if addr in self.watch_addresses:
                self.watch_addresses.remove(addr)
                self._set_status(f"Watch removed at 0x{addr:02X}")
            else:
                self._set_status(f"No watch at 0x{addr:02X}", is_error=True)
            self.refresh_ui()
        except Exception as exc:
            self._set_status(f"Remove watch failed: {exc}", is_error=True)

    def on_clear_watch(self) -> None:
        self.watch_addresses.clear()
        self._set_status("All watches cleared.")
        self.refresh_ui()

    def on_toggle_breakpoint_from_disasm(self, event: tk.Event) -> None:
        index_str = self.disasm_text.index(f"@{event.x},{event.y}")
        line_idx = int(index_str.split(".")[0]) - 1
        if line_idx < 0 or line_idx >= len(self.disasm_line_addresses):
            return
        addr = self.disasm_line_addresses[line_idx]
        if addr in self.breakpoints:
            self.breakpoints.remove(addr)
            self._set_status(f"Breakpoint removed at 0x{addr:02X}")
        else:
            self.breakpoints.add(addr)
            self._set_status(f"Breakpoint added at 0x{addr:02X}")
        self.refresh_ui()

    def on_run(self) -> None:
        if self.running:
            self.running = False
            self._set_status("Run loop paused.")
            return
        self.run_to_address = None
        self.running = True
        self._set_status("Run loop started.")
        self._run_loop_tick()

    def _run_loop_tick(self) -> None:
        if not self.running:
            return
        if self.cpu.halted:
            self.running = False
            self._set_status("CPU halted.")
            self.refresh_ui()
            return
        if self.run_to_address is not None and self.cpu.pc == self.run_to_address:
            target = self.run_to_address
            self.running = False
            self.run_to_address = None
            self._set_status(f"Reached run-to address 0x{target:02X}")
            self.refresh_ui()
            return
        if self.cpu.pc in self.breakpoints:
            bp = self.cpu.pc
            self.running = False
            self._set_status(f"Breakpoint hit at 0x{bp:02X}")
            self.refresh_ui()
            return
        if self._conditional_breakpoint_hit():
            self.running = False
            self._set_status(f"Conditional breakpoint hit: {self.conditional_breakpoint_raw}")
            self.refresh_ui()
            return
        try:
            self._execute_one_cycle_with_trace()
            self.refresh_ui()
            self.root.after(120, self._run_loop_tick)
        except Exception as exc:
            self.running = False
            self._set_status(str(exc), is_error=True)


def main() -> None:
    root = tk.Tk()
    app = EmulatorUI(root)
    app.refresh_ui()
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        messagebox.showerror("CPU Emulator", f"Failed to start UI: {exc}")
