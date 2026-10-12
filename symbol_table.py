from pathlib import Path
import ast
import re
import sys


REGISTERS_32 = {
    "EAX", "ECX", "EDX", "EBX", "ESP", "EBP", "ESI", "EDI"
}

REGISTERS_8 = {
    "AL", "CL", "DL", "BL", "AH", "CH", "DH", "BH"
}

REGISTERS_16 = {
    "AX", "CX", "DX", "BX", "SP", "BP", "SI", "DI"
}

SECTIONS = {
    ".data": "data",
    ".bss": "bss",
    ".text": "text"
}

DATA_DIRECTIVES = {"DB": 1, "DW": 2, "DD": 4}
RESERVE_DIRECTIVES = {"RESB": 1, "RESW": 2, "RESD": 4}

REG_REG_INSTRUCTIONS = {
    "MOV", "ADD", "SUB", "XOR", "AND", "OR", "CMP", "TEST"
}
REG_IMMEDIATE_INSTRUCTIONS = {
    "MOV", "ADD", "SUB", "XOR", "AND", "OR", "CMP"
}
CONDITIONAL_JUMPS = {
    "JE", "JZ", "JNE", "JNZ", "JG", "JGE", "JL", "JLE",
    "JA", "JAE", "JB", "JBE", "JO", "JNO", "JS", "JNS",
    "JP", "JNP"
}


def parse_number(value):
    value = value.strip().lower()

    if value.endswith("h") and value[:-1]:
        return int(value[:-1], 16)

    if value.endswith("b") and value[:-1] and re.fullmatch(r"[01]+b", value):
        return int(value[:-1], 2)

    return int(value, 0)


def split_values(value_text):
    values = []
    current = []
    quote = None
    escaped = False

    for char in value_text:
        if escaped:
            current.append(char)
            escaped = False
            continue

        if char == "\\" and quote:
            current.append(char)
            escaped = True
            continue

        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            current.append(char)
            continue

        if char == "," and quote is None:
            values.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    values.append("".join(current).strip())

    if any(not item for item in values):
        raise ValueError("Missing value in comma-separated declaration.")

    if quote is not None:
        raise ValueError("Unclosed quoted string.")

    return values


def decode_string(value):
    try:
        result = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        raise ValueError(f"Invalid quoted string: {value}")

    if not isinstance(result, str):
        raise ValueError(f"Invalid string value: {value}")

    try:
        return result.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("Only ASCII characters are supported in DB strings.")


def convert_data_value(directive, value_text):
    item_size = DATA_DIRECTIVES[directive]
    values = split_values(value_text)
    total_size = 0
    display_values = []

    for item in values:
        if item.startswith(("'", '"')):
            if directive != "DB":
                raise ValueError("Quoted strings are supported only with DB.")

            raw_bytes = decode_string(item)
            if not raw_bytes:
                raise ValueError("Empty strings are not supported.")

            total_size += len(raw_bytes)
            display_values.append(decode_string(item).decode('ascii'))
            continue

        try:
            number = parse_number(item)
        except ValueError:
            raise ValueError(
                f"Invalid numeric initialization '{item}' for {directive}."
            )

        bits = item_size * 8
        minimum = -(2 ** (bits - 1))
        maximum = (2 ** bits) - 1

        if number < minimum or number > maximum:
            raise ValueError(
                f"Value '{item}' does not fit in {bits} bits for {directive}."
            )

        total_size += item_size
        display_values.append(item)

    return total_size, ", ".join(display_values)


def get_register_size(register):
    register = register.upper()

    if register in REGISTERS_8:
        return 1
    if register in REGISTERS_16:
        return 2
    if register in REGISTERS_32:
        return 4

    return 0


def split_operands(text):
    result = []
    current = []
    square_brackets = 0
    quote = None

    for char in text:
        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None

        if quote is None:
            if char == "[":
                square_brackets += 1
            elif char == "]" and square_brackets:
                square_brackets -= 1
            elif char == "," and square_brackets == 0:
                result.append("".join(current).strip())
                current = []
                continue

        current.append(char)

    last = "".join(current).strip()
    if last:
        result.append(last)

    return result


def instruction_size(mnemonic, operand_text):
    mnemonic = mnemonic.upper()
    operands = split_operands(operand_text)

    if mnemonic in {"NOP", "RET", "LEAVE", "HLT", "CLC", "STC", "CLD", "STD"}:
        if operands:
            raise ValueError(f"{mnemonic} does not take operands.")
        return 1

    if mnemonic in {"PUSH", "POP"} and len(operands) == 1:
        operand = operands[0].upper()
        if get_register_size(operand) == 4:
            return 1
        if get_register_size(operand) == 2:
            return 2
        if mnemonic == "PUSH":
            try:
                number = parse_number(operand)
                return 2 if -128 <= number <= 127 else 5
            except ValueError:
                pass
        raise ValueError(f"Unsupported operand for {mnemonic}: {operand}")

    if mnemonic in {"INC", "DEC"} and len(operands) == 1:
        size = get_register_size(operands[0])
        if size == 4:
            return 1
        if size == 2:
            return 2
        if size == 1:
            return 2
        raise ValueError(f"Unsupported operand for {mnemonic}: {operands[0]}")

    if mnemonic == "MUL" and len(operands) == 1:
        operand = operands[0].upper()
        size = get_register_size(operand)

        if size in {1, 2, 4}:
            return 2 if size in {1, 4} else 3

        if operand.startswith("[") and operand.endswith("]"):
            return 6

        raise ValueError(f"Unsupported operand for MUL: {operands[0]}")

    if mnemonic == "INT" and len(operands) == 1:
        number = parse_number(operands[0])
        if not 0 <= number <= 255:
            raise ValueError("INT operand must be between 0 and 255.")
        return 2

    if mnemonic in {"CALL", "JMP"} and len(operands) == 1:
        return 5

    if mnemonic in CONDITIONAL_JUMPS and len(operands) == 1:
        return 6

    if mnemonic == "LOOP" and len(operands) == 1:
        return 2

    if len(operands) == 2:
        destination = operands[0].upper()
        source = operands[1].upper()
        destination_size = get_register_size(destination)
        source_size = get_register_size(source)

        if mnemonic in REG_REG_INSTRUCTIONS and destination_size and source_size:
            if destination_size != source_size:
                raise ValueError("Register operands must have matching sizes.")
            return 2 if destination_size in {1, 4} else 3

        if mnemonic in REG_IMMEDIATE_INSTRUCTIONS and destination_size:
            try:
                number = parse_number(operands[1])
            except ValueError:
                number = None

            if number is not None:
                if mnemonic == "MOV":
                    return 2 + destination_size
                if destination_size == 1:
                    if not -128 <= number <= 255:
                        raise ValueError("Immediate value does not fit in 8 bits.")
                    return 3
                if -128 <= number <= 127:
                    return 3
                return 2 + destination_size

        if destination_size and source.startswith("[") and source.endswith("]"):
            if mnemonic in {"MOV", "ADD", "SUB", "XOR", "AND", "OR", "CMP"}:
                return 6 if destination_size == 4 else 5

        if destination.startswith("[") and destination.endswith("]") and source_size:
            if mnemonic in {"MOV", "ADD", "SUB", "XOR", "AND", "OR", "CMP"}:
                return 6 if source_size == 4 else 5

    raise ValueError(
        f"Unsupported instruction or operand format: {mnemonic} {operand_text}".strip()
    )


def add_symbol(symbols, name, address, section, size, value, line_number):
    if name in symbols:
        previous_line = symbols[name]["line"]
        raise ValueError(
            f"Duplicate symbol '{name}'. It was already declared on line {previous_line}."
        )

    symbols[name] = {
        "name": name,
        "address": address,
        "section": section,
        "size": size,
        "value": value,
        "line": line_number
    }


def inspect_assembly(assembly_file):
    symbols = {}
    errors = []
    section_offsets = {".data": 0, ".bss": 0, ".text": 0}
    current_section = None
    statements = []

    try:
        with open(assembly_file, "r", encoding="utf-8") as file:
            for line_number, raw_line in enumerate(file, start=1):
                statement = raw_line.split(";", 1)[0].strip()
                if statement:
                    statements.append((line_number, statement))
    except FileNotFoundError:
        print(f"Error: assembly file '{assembly_file}' was not found.")
        return
    except OSError as error:
        print(f"Error: could not read assembly file: {error}")
        return

    for line_number, statement in statements:
        lower_statement = statement.lower()

        if lower_statement.startswith("section "):
            section_name = lower_statement.split(None, 1)[1].strip()
            if section_name not in SECTIONS:
                errors.append(
                    f"Line {line_number}: Unsupported section '{section_name}'."
                )
                current_section = None
            else:
                current_section = section_name
            continue

        if lower_statement in SECTIONS:
            current_section = lower_statement
            continue

        if lower_statement.startswith(("global ", "extern ", "bits ")):
            continue

        if current_section in {".data", ".bss"}:
            parts = statement.split(None, 2)
            if len(parts) < 2:
                errors.append(f"Line {line_number}: Invalid declaration.")
                continue

            name = parts[0]
            directive = parts[1].upper()

            if not re.fullmatch(r"[A-Za-z_.$?][A-Za-z0-9_.$?@]*", name):
                errors.append(f"Line {line_number}: Invalid symbol name '{name}'.")
                continue

            if directive in DATA_DIRECTIVES:
                if current_section != ".data":
                    errors.append(
                        f"Line {line_number}: {directive} declarations belong in .data."
                    )
                    continue
                if len(parts) < 3 or not parts[2].strip():
                    errors.append(
                        f"Line {line_number}: Missing initialization value for '{name}'."
                    )
                    continue

                try:
                    size, value = convert_data_value(directive, parts[2])
                    address = section_offsets[current_section]
                    add_symbol(
                        symbols, name, address, current_section, size, value, line_number
                    )
                    section_offsets[current_section] += size
                except ValueError as error:
                    errors.append(f"Line {line_number}: {error}")
                continue

            if directive in RESERVE_DIRECTIVES:
                if current_section != ".bss":
                    errors.append(
                        f"Line {line_number}: {directive} declarations belong in .bss."
                    )
                    continue
                if len(parts) < 3 or not parts[2].strip():
                    errors.append(
                        f"Line {line_number}: Missing reservation size for '{name}'."
                    )
                    continue

                try:
                    count = parse_number(parts[2])
                    if count <= 0:
                        raise ValueError("Reservation size must be a positive integer.")
                    size = count * RESERVE_DIRECTIVES[directive]
                    address = section_offsets[current_section]
                    add_symbol(
                        symbols, name, address, current_section, size,
                        "Uninitialized", line_number
                    )
                    section_offsets[current_section] += size
                except ValueError as error:
                    errors.append(f"Line {line_number}: Invalid reservation for '{name}': {error}")
                continue

            errors.append(
                f"Line {line_number}: Unsupported declaration directive '{directive}'."
            )

    current_section = None
    for line_number, statement in statements:
        lower_statement = statement.lower()

        if lower_statement.startswith("section "):
            section_name = lower_statement.split(None, 1)[1].strip()
            current_section = section_name if section_name in SECTIONS else None
            continue

        if lower_statement in SECTIONS:
            current_section = lower_statement
            continue

        if lower_statement.startswith(("global ", "extern ", "bits ")):
            continue

        if current_section != ".text":
            continue

        remaining = statement
        label_match = re.match(r"^([A-Za-z_.$?][A-Za-z0-9_.$?@]*):", remaining)

        if label_match:
            label = label_match.group(1)
            try:
                label_address = section_offsets[".text"]
                add_symbol(
                    symbols, label, label_address, ".text",
                    "Label", f"{label_address:08X}", line_number
                )
            except ValueError as error:
                errors.append(f"Line {line_number}: {error}")

            remaining = remaining[label_match.end():].strip()
            if not remaining:
                continue

        if remaining.endswith(":"):
            errors.append(f"Line {line_number}: Invalid label declaration '{remaining}'.")
            continue

        if not remaining:
            continue

        parts = remaining.split(None, 1)
        mnemonic = parts[0].upper()
        operand_text = parts[1] if len(parts) == 2 else ""

        try:
            size = instruction_size(mnemonic, operand_text)
            section_offsets[".text"] += size
        except (ValueError, TypeError) as error:
            errors.append(f"Line {line_number}: {error}")

    if errors:
        print("\n" + "=" * 68)
        print("ERRORS FOUND - SYMBOL TABLE NOT GENERATED")
        print("=" * 68)
        for error in errors:
            print(error)
        return

    print("\n" + "=" * 88)
    print("SYMBOL TABLE")
    print("=" * 88)
    print(
        f"{'Symbol Name':<18}"
        f"{'Symbol Address':<20}"
        f"{'Section':<12}"
        f"{'Symbol Size':<16}"
        f"{'Value':<22}"
    )
    print("-" * 88)

    for symbol in symbols.values():
        if symbol["section"] == ".text":
            address = f"{symbol['address']:08X}"
        else:
            address = f"{symbol['address']:08X}"

        size_text = (
            symbol["size"] if isinstance(symbol["size"], str)
            else f"{symbol['size']} byte(s)"
        )

        print(
            f"{symbol['name']:<18}"
            f"{address:<20}"
            f"{symbol['section']:<12}"
            f"{str(size_text):<16}"
            f"{symbol['value']:<22}"
        )

    print("-" * 88)
    print(f"Total symbols: {len(symbols)}")
    print("Symbol table generation completed.")


def main():
    if len(sys.argv) == 2:
        assembly_file = sys.argv[1]
    else:
        print("Symbol Table Generator")
        print("=" * 52)
        assembly_file = input("Enter assembly file name: ").strip()

    if not assembly_file:
        print("Error: assembly file name cannot be empty.")
        sys.exit(1)

    inspect_assembly(assembly_file)


if __name__ == "__main__":
    main()
