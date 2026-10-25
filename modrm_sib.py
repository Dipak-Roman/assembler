import re
import sys

REGISTERS_32 = {
    "EAX": 0, "ECX": 1, "EDX": 2, "EBX": 3,
    "ESP": 4, "EBP": 5, "ESI": 6, "EDI": 7
}
SCALE_BITS = {1: "00", 2: "01", 4: "10", 8: "11"}
DATA_SIZE = {"DB": 1, "DW": 2, "DD": 4, "RESB": 1, "RESW": 2, "RESD": 4}


def split_operands(text):
    operands, current = [], []
    depth, quote = 0, None
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
                operands.append("".join(current).strip())
                current = []
                continue
        current.append(char)
    last = "".join(current).strip()
    if last:
        operands.append(last)
    return operands


def parse_number(value):
    value = value.strip()
    try:
        if value.lower().startswith("0x"):
            return int(value, 16)
        if value.lower().endswith("h"):
            return int(value[:-1], 16)
        return int(value, 10)
    except ValueError:
        return None


def build_symbol_table(filename):
    symbols = {}
    offsets = {".data": 0, ".bss": 0, ".text": 0}
    current_section = ""

    try:
        with open(filename, "r", encoding="utf-8") as file:
            for line_number, raw_line in enumerate(file, start=1):
                statement = raw_line.split(";", 1)[0].strip()
                if not statement:
                    continue

                section_match = re.match(
                    r"^(?:SECTION\s+)?(\.(?:DATA|BSS|TEXT))\s*$", statement, re.I
                )
                if section_match:
                    current_section = section_match.group(1).lower()
                    continue

                if current_section in {".data", ".bss"}:
                    parts = statement.split(None, 2)
                    if len(parts) >= 2 and parts[1].upper() in DATA_SIZE:
                        name, directive = parts[0].upper(), parts[1].upper()
                        value = parts[2].strip() if len(parts) > 2 else ""
                        size = DATA_SIZE[directive]

                        if directive in {"DB", "DW", "DD"}:
                            if value.startswith(("'", '"')) and value.endswith(value[0]):
                                count = len(value[1:-1].encode("latin-1", errors="replace")) if directive == "DB" else 1
                            else:
                                count = len(split_operands(value)) if value else 1
                        else:
                            count = parse_number(value)
                            if count is None or count < 0:
                                continue

                        symbols[name] = {
                            "section": current_section,
                            "offset": offsets[current_section],
                            "line": line_number
                        }
                        offsets[current_section] += size * count
                        continue

                if current_section == ".text":
                    label_match = re.match(
                        r"^([A-Za-z_.$?][A-Za-z0-9_.$?@]*):", statement
                    )
                    if label_match:
                        name = label_match.group(1).upper()
                        symbols[name] = {
                            "section": ".text",
                            "offset": offsets[".text"],
                            "line": line_number
                        }
    except FileNotFoundError:
        return None, f"Assembly file '{filename}' was not found."
    except OSError as error:
        return None, f"Could not read assembly file '{filename}': {error}"

    return symbols, None


def parse_memory_expression(operand, symbols):
    if not (operand.startswith("[") and operand.endswith("]")):
        return None, "Memory operand must be enclosed in square brackets."

    expression = operand[1:-1].replace(" ", "").upper()
    if not expression:
        return None, "Memory expression cannot be empty."

    terms = re.findall(r"[+-]?[^+-]+", expression)
    base, index, symbol_name = None, None, None
    scale, displacement = 1, 0

    for term in terms:
        sign = 1
        if term.startswith("-"):
            sign, term = -1, term[1:]
        elif term.startswith("+"):
            term = term[1:]
        if not term:
            continue

        if "*" in term:
            pieces = term.split("*")
            if len(pieces) != 2 or pieces[0] not in REGISTERS_32:
                return None, f"Invalid index expression '{term}'."
            parsed_scale = parse_number(pieces[1])
            if parsed_scale not in SCALE_BITS:
                return None, "SIB scale must be 1, 2, 4, or 8."
            if sign < 0 or index is not None:
                return None, "Negative or multiple index terms are not supported."
            index, scale = pieces[0], parsed_scale
        elif term in REGISTERS_32:
            if sign < 0:
                return None, "Negative register terms are not supported."
            if base is None:
                base = term
            elif index is None:
                index = term
                scale = 1
            else:
                return None, "Too many registers in memory expression."
        else:
            number = parse_number(term)
            if number is not None:
                displacement += sign * number
            elif re.fullmatch(r"[A-Z_.$?][A-Z0-9_.$?@]*", term):
                if sign < 0:
                    return None, "Negative symbol terms are not supported."
                if symbol_name is not None:
                    return None, "Only one symbol term is supported."
                if term not in symbols:
                    return None, f"Undefined symbol '{term}'."
                symbol_name = term
            else:
                return None, f"Unsupported memory term '{term}'."

    if index == "ESP":
        return None, "ESP cannot be used as an index register."

    symbol_info = symbols.get(symbol_name) if symbol_name else None
    return {
        "base": base, "index": index, "scale": scale,
        "displacement": displacement, "symbol": symbol_name,
        "symbol_info": symbol_info
    }, None


def make_modrm(mod, reg, rm):
    bits = f"{mod:02b}{reg:03b}{rm:03b}"
    return {"binary": bits, "hex": f"{int(bits, 2):02X}"}


def make_sib(scale, index, base):
    bits = f"{SCALE_BITS[scale]}{index:03b}{base:03b}"
    return {"binary": bits, "hex": f"{int(bits, 2):02X}"}


def encode_memory_address(operand, symbols, reg_field):
    memory, error = parse_memory_expression(operand, symbols)
    if error:
        return None, error

    base, index = memory["base"], memory["index"]
    displacement = memory["displacement"]
    if memory["symbol"]:
        displacement += memory["symbol_info"]["offset"]

    if not -2147483648 <= displacement <= 2147483647:
        return None, "Displacement is outside the signed 32-bit range."

    sib = None
    if base is None:
        mod, disp_size, disp_note = 0, 32, "disp32"
        if index is None:
            rm = 5
        else:
            rm = 4
            sib = make_sib(memory["scale"], REGISTERS_32[index], 5)
    else:
        needs_sib = index is not None or base == "ESP"
        if displacement == 0 and base != "EBP":
            mod, disp_size, disp_note = 0, 0, "no displacement"
        elif -128 <= displacement <= 127:
            mod, disp_size, disp_note = 1, 8, "disp8"
        else:
            mod, disp_size, disp_note = 2, 32, "disp32"

        if needs_sib:
            rm = 4
            index_code = REGISTERS_32[index] if index else 4
            sib = make_sib(memory["scale"], index_code, REGISTERS_32[base])
        else:
            rm = REGISTERS_32[base]

        if base == "EBP" and mod == 0:
            mod, disp_size, disp_note = 1, 8, "disp8 (zero)"
            displacement = 0

    return {
        "modrm": make_modrm(mod, reg_field, rm),
        "sib": sib,
        "displacement": displacement,
        "displacement_size": disp_size,
        "displacement_note": disp_note,
        "address": memory
    }, None


def register_field_for_instruction(mnemonic, operands, memory_operand):
    """Use the register operand for common MOV direction forms."""
    if mnemonic.upper() != "MOV" or len(operands) != 2:
        return None, "REG-field inference currently supports MOV with two operands."

    first, second = operands[0].strip(), operands[1].strip()
    if first.upper() == memory_operand.upper():
        register_operand = second.upper()
    elif second.upper() == memory_operand.upper():
        register_operand = first.upper()
    else:
        return None, "Could not identify the register paired with the memory operand."

    if register_operand not in REGISTERS_32:
        return None, f"Expected a 32-bit register next to memory operand, got '{register_operand}'."

    return REGISTERS_32[register_operand], None


def display_result(operand, result, mnemonic, reg_name):
    info = result["address"]
    print(f"Memory operand : {operand}")
    print(f"Instruction    : {mnemonic}")
    print(f"Register field : {reg_name} ({REGISTERS_32[reg_name]:03b})")
    print(f"Base register  : {info['base'] or 'None'}")
    print(f"Index register : {info['index'] or 'None'}")
    print(f"Scale          : {info['scale']}")

    if info["symbol"]:
        symbol_info = info["symbol_info"]
        print(f"Symbol         : {info['symbol']}")
        print(f"Symbol section : {symbol_info['section']}")
        print(f"Symbol offset  : 0x{symbol_info['offset']:08X} (section-relative)")

    print(f"Displacement   : {result['displacement']} (0x{result['displacement'] & 0xFFFFFFFF:08X})")
    print(f"ModR/M         : {result['modrm']['binary']} (binary), {result['modrm']['hex']} (hex)")
    if result["sib"]:
        print(f"SIB            : {result['sib']['binary']} (binary), {result['sib']['hex']} (hex)")
    else:
        print("SIB            : Not required")
    print(f"Displacement   : {result['displacement_note']}")


def inspect_assembly_file(filename):
    symbols, error = build_symbol_table(filename)
    if error:
        print(f"Error: {error}")
        return

    try:
        with open(filename, "r", encoding="utf-8") as file:
            found = False
            for line_number, raw_line in enumerate(file, start=1):
                statement = raw_line.split(";", 1)[0].strip()
                if not statement:
                    continue

                label_match = re.match(r"^[A-Za-z_.$?][A-Za-z0-9_.$?@]*:\s*", statement)
                if label_match:
                    statement = statement[label_match.end():].strip()
                if not statement:
                    continue

                parts = statement.split(None, 1)
                if len(parts) < 2:
                    continue
                mnemonic, operand_text = parts[0].upper(), parts[1]
                operands = split_operands(operand_text)

                for original_operand in operands:
                    operand = re.sub(
                        r"^(BYTE|WORD|DWORD|QWORD|TBYTE)\s*", "", original_operand.strip(), flags=re.I
                    )
                    if not (operand.startswith("[") and operand.endswith("]")):
                        continue

                    found = True
                    reg_field, reg_error = register_field_for_instruction(mnemonic, operands, original_operand)
                    print(f"\nLine {line_number}: {statement}")
                    if reg_error:
                        print(f"Error: {reg_error}")
                        continue

                    register_name = next(name for name, code in REGISTERS_32.items() if code == reg_field)
                    result, error = encode_memory_address(operand, symbols, reg_field)
                    if error:
                        print(f"Error: {error}")
                    else:
                        display_result(operand, result, mnemonic, register_name)

            if not found:
                print("No memory operands in square brackets were found in the file.")
    except FileNotFoundError:
        print(f"Error: assembly file '{filename}' was not found.")
    except OSError as error:
        print(f"Error: could not read '{filename}': {error}")


def main():
    if len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        print("ModR/M and SIB Byte Generator")
        print("=" * 36)
        filename = input("Enter assembly file name: ").strip()

    if not filename:
        print("Error: assembly file name cannot be empty.")
        sys.exit(1)
    inspect_assembly_file(filename)


if __name__ == "__main__":
    main()
