"""
IA-32 Pass 2 - Machine Code Generator (initial supported subset)

This is an educational 32-bit IA-32 encoder. It emits raw .text bytes for the
instruction forms explicitly implemented below. It does not create ELF/PE
executables, resolve external symbols, or support every x86 addressing form.

Usage:
    python3 pass2.py program.asm
"""

import re
import sys
import ast

REG32 = {
    "EAX": 0, "ECX": 1, "EDX": 2, "EBX": 3,
    "ESP": 4, "EBP": 5, "ESI": 6, "EDI": 7,
}

REG8 = {
    "AL": 0, "CL": 1, "DL": 2, "BL": 3,
    "AH": 4, "CH": 5, "DH": 6, "BH": 7,
}

REG16 = {
    "AX": 0, "CX": 1, "DX": 2, "BX": 3,
    "SP": 4, "BP": 5, "SI": 6, "DI": 7,
}

CONDITIONAL_JUMPS = {
    "JO": 0x80, "JNO": 0x81, "JB": 0x82, "JAE": 0x83,
    "JE": 0x84, "JZ": 0x84, "JNE": 0x85, "JNZ": 0x85,
    "JBE": 0x86, "JA": 0x87, "JS": 0x88, "JNS": 0x89,
    "JP": 0x8A, "JNP": 0x8B, "JL": 0x8C, "JGE": 0x8D,
    "JLE": 0x8E, "JG": 0x8F,
}

NO_OPERAND = {
    "NOP": bytes([0x90]), "RET": bytes([0xC3]),
    "HLT": bytes([0xF4]), "LEAVE": bytes([0xC9]),
    "CLC": bytes([0xF8]), "STC": bytes([0xF9]),
    "CLD": bytes([0xFC]), "STD": bytes([0xFD]),
}


def parse_number(text):
    text = text.strip().lower()
    if text.endswith("h") and text[:-1]:
        return int(text[:-1], 16)
    if text.endswith("b") and re.fullmatch(r"[01]+b", text):
        return int(text[:-1], 2)
    return int(text, 0)


def split_operands(text):
    result, current = [], []
    quote = None
    depth = 0
    for char in text:
        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
        if quote is None:
            if char == "[":
                depth += 1
            elif char == "]" and depth:
                depth -= 1
            elif char == "," and depth == 0:
                result.append("".join(current).strip())
                current = []
                continue
        current.append(char)
    last = "".join(current).strip()
    if last:
        result.append(last)
    if quote is not None:
        raise ValueError("Unclosed quoted string.")
    return result


def strip_size(operand):
    return re.sub(r"^(BYTE|WORD|DWORD|QWORD)\s+", "", operand.strip(), flags=re.I).strip()


def clean_source(filename):
    lines = []
    try:
        with open(filename, "r", encoding="utf-8") as source:
            for line_no, raw in enumerate(source, 1):
                statement = raw.split(";", 1)[0].strip()
                if statement:
                    lines.append((line_no, statement))
    except OSError as error:
        raise ValueError(f"Could not read '{filename}': {error}")
    return lines


def parse_source(lines):
    """Collect instructions, section-relative labels, and data symbols."""
    section = None
    records = []
    symbols = {}
    offsets = {".text": 0, ".data": 0, ".bss": 0}

    for line_no, original in lines:
        statement = original
        match = re.fullmatch(r"(?:section\s+)?(\.text|\.data|\.bss)", statement, re.I)
        if match:
            section = match.group(1).lower()
            continue
        if statement.lower().startswith(("global ", "extern ", "bits ")):
            continue

        label = None
        label_match = re.match(r"^([A-Za-z_.$?][\w.$?@]*):\s*(.*)$", statement)
        if label_match:
            label, statement = label_match.groups()
            if label.upper() in symbols:
                raise ValueError(f"Line {line_no}: duplicate symbol '{label}'.")
            if section != ".text":
                raise ValueError(f"Line {line_no}: labels are only supported in .text.")
            symbols[label.upper()] = {"section": ".text", "address": offsets[".text"], "kind": "label"}
            if not statement.strip():
                continue
            statement = statement.strip()

        if section is None:
            raise ValueError(f"Line {line_no}: statement outside a recognized section.")

        parts = statement.split(None, 1)
        operation = parts[0].upper()
        operand_text = parts[1].strip() if len(parts) > 1 else ""

        if section == ".text":
            operands = split_operands(operand_text)
            size = instruction_size(operation, operands)
            records.append({
                "line": line_no, "section": section, "address": offsets[section],
                "size": size, "operation": operation, "operands": operands,
                "source": original
            })
            offsets[section] += size
        elif section == ".data":
            if len(parts) < 2:
                raise ValueError(f"Line {line_no}: invalid data declaration.")
            # NASM-like declaration: name db/dw/dd value
            data_parts = statement.split(None, 2)
            if len(data_parts) != 3:
                raise ValueError(f"Line {line_no}: expected 'name db/dw/dd value'.")
            name, directive, value_text = data_parts
            directive = directive.upper()
            widths = {"DB": 1, "DW": 2, "DD": 4}
            if directive not in widths:
                raise ValueError(f"Line {line_no}: unsupported data directive '{directive}'.")
            if name.upper() in symbols:
                raise ValueError(f"Line {line_no}: duplicate symbol '{name}'.")
            values = split_operands(value_text)
            data_bytes = bytearray()
            for value in values:
                value = value.strip()
                if value.startswith(("'", '"')):
                    if directive != "DB":
                        raise ValueError(f"Line {line_no}: strings are only supported with DB.")
                    try:
                        data_bytes.extend(ast.literal_eval(value).encode("ascii"))
                    except (ValueError, SyntaxError, UnicodeEncodeError):
                        raise ValueError(f"Line {line_no}: invalid ASCII string {value}.")
                else:
                    number = parse_number(value)
                    bits = widths[directive] * 8
                    if not -(1 << (bits - 1)) <= number < (1 << bits):
                        raise ValueError(f"Line {line_no}: value {value} does not fit {directive}.")
                    data_bytes.extend((number & ((1 << bits) - 1)).to_bytes(widths[directive], "little"))
            symbols[name.upper()] = {
                "section": ".data", "address": offsets[section], "kind": "data",
                "size": len(data_bytes), "bytes": bytes(data_bytes)
            }
            records.append({
                "line": line_no, "section": section, "address": offsets[section],
                "size": len(data_bytes), "operation": directive, "operands": [name, value_text],
                "source": original, "data_bytes": bytes(data_bytes)
            })
            offsets[section] += len(data_bytes)
        elif section == ".bss":
            data_parts = statement.split(None, 2)
            reserve_widths = {"RESB": 1, "RESW": 2, "RESD": 4}
            if len(data_parts) != 3 or data_parts[1].upper() not in reserve_widths:
                raise ValueError(f"Line {line_no}: expected 'name resb/resw/resd count'.")
            name, directive, count_text = data_parts
            count = parse_number(count_text)
            if count <= 0:
                raise ValueError(f"Line {line_no}: reservation count must be positive.")
            if name.upper() in symbols:
                raise ValueError(f"Line {line_no}: duplicate symbol '{name}'.")
            size = reserve_widths[directive.upper()] * count
            symbols[name.upper()] = {"section": ".bss", "address": offsets[section], "kind": "bss", "size": size}
            records.append({
                "line": line_no, "section": section, "address": offsets[section],
                "size": size, "operation": directive.upper(), "operands": [name, count_text],
                "source": original
            })
            offsets[section] += size

    # Check branch target names after collecting all labels.
    for record in records:
        if record["section"] == ".text" and record["operation"] in (set(CONDITIONAL_JUMPS) | {"JMP", "CALL", "LOOP"}):
            if len(record["operands"]) != 1:
                continue
            target = record["operands"][0].upper()
            if target not in symbols or symbols[target]["kind"] != "label":
                raise ValueError(f"Line {record['line']}: unknown code label '{record['operands'][0]}'.")

    return records, symbols, offsets


def instruction_size(mnemonic, operands):
    """Size pass matching the initial encoding subset below."""
    ops = [strip_size(x) for x in operands]
    if mnemonic in NO_OPERAND and not ops:
        return 1
    if mnemonic == "INT" and len(ops) == 1:
        n = parse_number(ops[0])
        if not 0 <= n <= 255:
            raise ValueError("INT immediate must be in range 0..255.")
        return 2
    if mnemonic == "MOV" and len(ops) == 2:
        dst, src = ops[0].upper(), ops[1].upper()
        if dst in REG32 and is_number(src):
            return 5
        if dst in REG32 and src in REG32:
            return 2
        if dst in REG32 and is_memory(src):
            return 6  # MOV r32, [absolute disp32]
        if is_memory(dst) and src in REG32:
            return 6  # MOV [absolute disp32], r32
    if mnemonic in {"ADD", "SUB", "CMP", "AND", "OR", "XOR"} and len(ops) == 2:
        dst, src = ops[0].upper(), ops[1].upper()
        if dst in REG32 and src in REG32:
            return 2
        if dst in REG32 and is_number(src):
            n = parse_number(src)
            return 3 if -128 <= n <= 127 else 6
    if mnemonic in {"INC", "DEC"} and len(ops) == 1 and ops[0].upper() in REG32:
        return 1
    if mnemonic == "MUL" and len(ops) == 1 and ops[0].upper() in REG32:
        return 2
    if mnemonic in CONDITIONAL_JUMPS and len(ops) == 1:
        return 6
    if mnemonic in {"JMP", "CALL"} and len(ops) == 1:
        return 5
    if mnemonic == "LOOP" and len(ops) == 1:
        return 2
    raise ValueError(f"unsupported instruction format: {mnemonic} {' , '.join(ops)}")


def is_number(text):
    try:
        parse_number(text)
        return True
    except ValueError:
        return False


def is_memory(text):
    return text.startswith("[") and text.endswith("]")


def little_endian(value, size):
    return (value & ((1 << (size * 8)) - 1)).to_bytes(size, "little")


def memory_symbol(operand, symbols, line_no):
    text = strip_size(operand).strip()
    if not is_memory(text):
        raise ValueError(f"Line {line_no}: expected a [symbol] memory operand.")
    name = text[1:-1].strip().upper()
    if name not in symbols or symbols[name]["section"] not in {".data", ".bss"}:
        raise ValueError(f"Line {line_no}: unknown data symbol '{name}'.")
    # This initial assembler uses section-relative offsets as disp32 for educational output.
    # A real object file/linker must relocate section references.
    return symbols[name]["address"]


def encode_instruction(record, symbols):
    mnemonic = record["operation"]
    ops = [strip_size(x) for x in record["operands"]]
    line_no = record["line"]
    address = record["address"]

    if mnemonic in NO_OPERAND:
        return NO_OPERAND[mnemonic]
    if mnemonic == "INT":
        return bytes([0xCD, parse_number(ops[0])])

    if mnemonic == "MOV" and len(ops) == 2:
        dst, src = ops[0].upper(), ops[1].upper()
        if dst in REG32 and is_number(src):
            return bytes([0xB8 + REG32[dst]]) + little_endian(parse_number(src), 4)
        if dst in REG32 and src in REG32:
            # 89 /r: MOV r/m32, r32; destination is r/m, source is reg
            modrm = 0xC0 | (REG32[src] << 3) | REG32[dst]
            return bytes([0x89, modrm])
        if dst in REG32 and is_memory(src):
            disp = memory_symbol(src, symbols, line_no)
            modrm = 0x05 | (REG32[dst] << 3)  # mod=00, r/m=101 absolute disp32
            return bytes([0x8B, modrm]) + little_endian(disp, 4)
        if is_memory(dst) and src in REG32:
            disp = memory_symbol(dst, symbols, line_no)
            modrm = 0x05 | (REG32[src] << 3)
            return bytes([0x89, modrm]) + little_endian(disp, 4)

    if mnemonic in {"ADD", "SUB", "CMP", "AND", "OR", "XOR"} and len(ops) == 2:
        dst, src = ops[0].upper(), ops[1].upper()
        if dst in REG32 and src in REG32:
            opcode = {"ADD": 0x01, "OR": 0x09, "AND": 0x21, "SUB": 0x29, "XOR": 0x31, "CMP": 0x39}[mnemonic]
            modrm = 0xC0 | (REG32[src] << 3) | REG32[dst]
            return bytes([opcode, modrm])
        if dst in REG32 and is_number(src):
            value = parse_number(src)
            # Use 83 /digit ib for signed 8-bit immediate; otherwise 81 /digit id.
            extension = {"ADD": 0, "OR": 1, "AND": 4, "SUB": 5, "XOR": 6, "CMP": 7}[mnemonic]
            if -128 <= value <= 127:
                return bytes([0x83, 0xC0 | (extension << 3) | REG32[dst], value & 0xFF])
            return bytes([0x81, 0xC0 | (extension << 3) | REG32[dst]]) + little_endian(value, 4)

    if mnemonic in {"INC", "DEC"} and len(ops) == 1 and ops[0].upper() in REG32:
        reg = REG32[ops[0].upper()]
        # Legacy 32-bit register encodings in 32-bit mode.
        return bytes([(0x40 if mnemonic == "INC" else 0x48) + reg])

    if mnemonic == "MUL" and len(ops) == 1 and ops[0].upper() in REG32:
        return bytes([0xF7, 0xE0 | REG32[ops[0].upper()]])  # F7 /4

    if mnemonic in CONDITIONAL_JUMPS and len(ops) == 1:
        target = symbols[ops[0].upper()]["address"]
        displacement = target - (address + 6)
        if not -(1 << 31) <= displacement < (1 << 31):
            raise ValueError(f"Line {line_no}: conditional jump displacement is out of range.")
        return bytes([0x0F, CONDITIONAL_JUMPS[mnemonic]]) + little_endian(displacement, 4)

    if mnemonic in {"JMP", "CALL"} and len(ops) == 1:
        target = symbols[ops[0].upper()]["address"]
        displacement = target - (address + 5)
        opcode = 0xE9 if mnemonic == "JMP" else 0xE8
        return bytes([opcode]) + little_endian(displacement, 4)

    if mnemonic == "LOOP" and len(ops) == 1:
        target = symbols[ops[0].upper()]["address"]
        displacement = target - (address + 2)
        if not -128 <= displacement <= 127:
            raise ValueError(f"Line {line_no}: LOOP target is outside short-jump range.")
        return bytes([0xE2, displacement & 0xFF])

    raise ValueError(f"Line {line_no}: encoding not implemented for '{record['source']}'.")


def assemble(filename):
    lines = clean_source(filename)
    records, symbols, section_sizes = parse_source(lines)
    encoded = []
    errors = []

    for record in records:
        if record["section"] == ".text":
            try:
                machine = encode_instruction(record, symbols)
                if len(machine) != record["size"]:
                    raise ValueError(
                        f"internal size mismatch: Pass 1 expected {record['size']} byte(s), "
                        f"encoder produced {len(machine)}."
                    )
                record["machine"] = machine
                encoded.extend(machine)
            except (ValueError, KeyError) as error:
                errors.append(str(error))
        elif record["section"] == ".data":
            record["machine"] = record["data_bytes"]
        else:
            record["machine"] = b""

    if errors:
        print("\nPASS 2 FAILED - NO OUTPUT FILE WRITTEN")
        for error in errors:
            print("  " + error)
        return

    print("\n" + "=" * 100)
    print("PASS 2 - MACHINE CODE LISTING")
    print("=" * 100)
    print(f"{'Address':<12}{'Machine code':<32}Source")
    print("-" * 100)
    for record in records:
        if record["section"] == ".text":
            hex_bytes = " ".join(f"{byte:02X}" for byte in record["machine"])
            print(f"{record['address']:08X}    {hex_bytes:<32}{record['source']}")
    print("-" * 100)
    print(f"Generated .text size: {len(encoded)} byte(s)")
    print("Note: data/BSS are reported in tables but are not linked into a loadable executable.")

    output_name = filename.rsplit(".", 1)[0] + ".bin"
    try:
        with open(output_name, "wb") as output:
            output.write(bytes(encoded))
    except OSError as error:
        print(f"Could not write output file: {error}")
        return
    print(f"Raw .text binary written to: {output_name}")

    print("\nSYMBOL TABLE (section-relative offsets)")
    print("-" * 62)
    print(f"{'Name':<18}{'Section':<12}{'Offset':<14}{'Kind'}")
    for name, info in symbols.items():
        print(f"{name:<18}{info['section']:<12}{info['address']:08X}      {info['kind']}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 pass2.py <assembly_file.asm>")
        sys.exit(1)
    try:
        assemble(sys.argv[1])
    except (ValueError, OSError) as error:
        print(f"Assembler error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
