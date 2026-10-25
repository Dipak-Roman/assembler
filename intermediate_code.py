from pathlib import Path
import re
import sys


SECTIONS = {".data", ".bss", ".text"}
DATA_DIRECTIVES = {"DB", "DW", "DD"}
RESERVE_DIRECTIVES = {"RESB", "RESW", "RESD"}
REGISTERS = {
    "AL", "AH", "BL", "BH", "CL", "CH", "DL", "DH",
    "AX", "BX", "CX", "DX", "SI", "DI", "SP", "BP",
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "ESP", "EBP"
}


def split_operands(text):
    operands = []
    current = []
    bracket_depth = 0
    quote = None

    for char in text:
        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None

        if quote is None:
            if char == "[":
                bracket_depth += 1
            elif char == "]" and bracket_depth > 0:
                bracket_depth -= 1
            elif char == "," and bracket_depth == 0:
                operands.append("".join(current).strip())
                current = []
                continue

        current.append(char)

    last = "".join(current).strip()
    if last:
        operands.append(last)

    return operands


def classify_operand(operand):
    value = operand.strip()
    upper_value = value.upper()

    if upper_value in REGISTERS:
        return "Register"

    if value.startswith("[") and value.endswith("]"):
        return "Memory"

    if re.fullmatch(r"[+-]?(?:0[xX][0-9A-Fa-f]+|\d+|[0-9A-Fa-f]+[Hh])", value):
        return "Literal"

    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return "Literal"

    return "Symbol"


def parse_statement(statement):
    label = ""
    match = re.match(r"^([A-Za-z_.$?][A-Za-z0-9_.$?@]*):\s*(.*)$", statement)

    if match:
        label = match.group(1)
        statement = match.group(2).strip()

    return label, statement


def generate_intermediate_code(assembly_file):
    intermediate_code = []
    literals = []
    errors = []
    current_section = ""
    literal_lookup = {}

    try:
        with open(assembly_file, "r", encoding="utf-8") as file:
            for line_number, raw_line in enumerate(file, start=1):
                statement = raw_line.split(";", 1)[0].strip()

                if not statement:
                    continue

                label, statement = parse_statement(statement)

                if not statement and label:
                    intermediate_code.append({
                        "line": line_number,
                        "section": current_section or "—",
                        "label": label,
                        "operation": "LABEL",
                        "operand1": "",
                        "operand2": ""
                    })
                    continue

                lower_statement = statement.lower()

                if lower_statement.startswith("section "):
                    section = lower_statement.split(None, 1)[1].strip()

                    if section not in SECTIONS:
                        errors.append(
                            f"Line {line_number}: Unsupported section '{section}'."
                        )
                        continue

                    current_section = section
                    intermediate_code.append({
                        "line": line_number,
                        "section": current_section,
                        "label": label,
                        "operation": "SECTION",
                        "operand1": section,
                        "operand2": ""
                    })
                    continue

                if lower_statement in SECTIONS:
                    current_section = lower_statement
                    intermediate_code.append({
                        "line": line_number,
                        "section": current_section,
                        "label": label,
                        "operation": "SECTION",
                        "operand1": current_section,
                        "operand2": ""
                    })
                    continue

                if lower_statement.startswith(("global ", "extern ", "bits ")):
                    parts = statement.split(None, 1)
                    intermediate_code.append({
                        "line": line_number,
                        "section": current_section or "—",
                        "label": label,
                        "operation": parts[0].upper(),
                        "operand1": parts[1] if len(parts) > 1 else "",
                        "operand2": ""
                    })
                    continue

                parts = statement.split(None, 2)

                if current_section in {".data", ".bss"}:
                    if len(parts) < 2:
                        errors.append(f"Line {line_number}: Invalid data declaration.")
                        continue

                    symbol_name = parts[0]
                    directive = parts[1].upper()
                    value = parts[2].strip() if len(parts) == 3 else ""

                    if directive not in DATA_DIRECTIVES | RESERVE_DIRECTIVES:
                        errors.append(
                            f"Line {line_number}: Unsupported declaration '{directive}'."
                        )
                        continue

                    if not value:
                        errors.append(
                            f"Line {line_number}: Missing value or reservation size for '{symbol_name}'."
                        )
                        continue

                    intermediate_code.append({
                        "line": line_number,
                        "section": current_section,
                        "label": label or symbol_name,
                        "operation": directive,
                        "operand1": value,
                        "operand2": ""
                    })

                    if directive in DATA_DIRECTIVES:
                        for literal in split_operands(value):
                            if (
                                len(literal) >= 2
                                and literal[0] in ("'", '"')
                                and literal[-1] == literal[0]
                            ):
                                if literal not in literal_lookup:
                                    literal_lookup[literal] = f"L{len(literals) + 1}"
                                    literals.append({
                                        "id": literal_lookup[literal],
                                        "value": literal,
                                        "source_line": line_number
                                    })
                    continue

                if current_section == ".text":
                    instruction_parts = statement.split(None, 1)
                    mnemonic = instruction_parts[0].upper()
                    operand_text = (
                        instruction_parts[1] if len(instruction_parts) > 1 else ""
                    )
                    operands = split_operands(operand_text)

                    if len(operands) > 2:
                        errors.append(
                            f"Line {line_number}: More than two operands are not supported."
                        )
                        continue

                    intermediate_code.append({
                        "line": line_number,
                        "section": current_section,
                        "label": label,
                        "operation": mnemonic,
                        "operand1": operands[0] if operands else "",
                        "operand2": operands[1] if len(operands) > 1 else ""
                    })

                    for operand in operands:
                        if classify_operand(operand) == "Literal":
                            if operand not in literal_lookup:
                                literal_lookup[operand] = f"L{len(literals) + 1}"
                                literals.append({
                                    "id": literal_lookup[operand],
                                    "value": operand,
                                    "source_line": line_number
                                })
                    continue

                errors.append(
                    f"Line {line_number}: Statement is outside a recognized section."
                )

    except FileNotFoundError:
        print(f"Error: assembly file '{assembly_file}' was not found.")
        return
    except OSError as error:
        print(f"Error: could not read assembly file: {error}")
        return

    if errors:
        print("\nErrors found. Intermediate code was not generated.")
        for error in errors:
            print(error)
        return

    print("\n" + "=" * 104)
    print("INTERMEDIATE CODE")
    print("=" * 104)
    print(
        f"{'Index':<7}{'Line':<7}{'Section':<12}{'Label':<18}"
        f"{'Operation':<14}{'Operand 1':<22}{'Operand 2':<22}"
    )
    print("-" * 104)

    for index, record in enumerate(intermediate_code, start=1):
        print(
            f"{index:<7}{record['line']:<7}{record['section']:<12}"
            f"{record['label'] or '—':<18}{record['operation']:<14}"
            f"{record['operand1'] or '—':<22}{record['operand2'] or '—':<22}"
        )

    print("\n" + "=" * 60)
    print("LITERAL TABLE")
    print("=" * 60)
    print(f"{'Literal ID':<14}{'Literal Value':<28}{'Source Line':<12}")
    print("-" * 60)

    if literals:
        for literal in literals:
            print(
                f"{literal['id']:<14}{literal['value']:<28}"
                f"{literal['source_line']:<12}"
            )
    else:
        print("No literals found.")

    print("-" * 60)
    print(f"Intermediate code records: {len(intermediate_code)}")
    print(f"Unique literals: {len(literals)}")


def main():
    if len(sys.argv) == 2:
        assembly_file = sys.argv[1]
    else:
        print("IA-32 Intermediate Code Generator")
        print("=" * 52)
        assembly_file = input("Enter assembly file name: ").strip()

    if not assembly_file:
        print("Error: assembly file name cannot be empty.")
        sys.exit(1)

    generate_intermediate_code(assembly_file)


if __name__ == "__main__":
    main()
