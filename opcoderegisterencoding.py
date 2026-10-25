import re
import sys

REGISTER_CODES = {
    "EAX": "000",
    "ECX": "001",
    "EDX": "010",
    "EBX": "011",
    "ESP": "100",
    "EBP": "101",
    "ESI": "110",
    "EDI": "111",
    "AX": "000",
    "CX": "001",
    "DX": "010",
    "BX": "011",
    "SP": "100",
    "BP": "101",
    "SI": "110",
    "DI": "111",
    "AL": "000",
    "CL": "001",
    "DL": "010",
    "BL": "011",
    "AH": "100",
    "CH": "101",
    "DH": "110",
    "BH": "111",
}

SECTIONS = {".data", ".bss", ".text"}
DATA_DIRECTIVES = {"DB", "DW", "DD", "RESB", "RESW", "RESD"}

# Opcode descriptions are references for common IA-32 forms, not full machine-code output.
OPCODE_FORMS = {
    "MOV": "Register, memory, and immediate forms (e.g. 89 /r, 8B /r, B8+rd, C7 /0)",
    "ADD": "Register/memory forms (e.g. 01 /r, 03 /r); immediate forms (80 /0, 81 /0, 83 /0)",
    "SUB": "Register/memory forms (e.g. 29 /r, 2B /r); immediate forms (80 /5, 81 /5, 83 /5)",
    "MUL": "Unsigned multiply: F6 /4 for 8-bit, F7 /4 for 16/32-bit operand",
    "IMUL": "Signed multiply; encoding depends on operand count and size",
    "DIV": "Unsigned divide: F6 /6 for 8-bit, F7 /6 for 16/32-bit operand",
    "IDIV": "Signed divide: F6 /7 for 8-bit, F7 /7 for 16/32-bit operand",
    "INC": "FF /0 (or legacy 40+rd for 16/32-bit register)",
    "DEC": "FF /1 (or legacy 48+rd for 16/32-bit register)",
    "PUSH": "Register, memory, or immediate forms (e.g. 50+rd, FF /6, 68 id, 6A ib)",
    "POP": "Register or memory forms (e.g. 58+rd, 8F /0)",
    "CMP": "Register/memory forms (e.g. 39 /r, 3B /r); immediate forms (80 /7, 81 /7, 83 /7)",
    "AND": "Register/memory forms (e.g. 21 /r, 23 /r); immediate forms (80 /4, 81 /4, 83 /4)",
    "OR": "Register/memory forms (e.g. 09 /r, 0B /r); immediate forms (80 /1, 81 /1, 83 /1)",
    "XOR": "Register/memory forms (e.g. 31 /r, 33 /r); immediate forms (80 /6, 81 /6, 83 /6)",
    "JMP": "Short EB cb, near E9 cd, or indirect FF /4",
    "JE": "Short 74 cb or near 0F 84 cd",
    "JZ": "Short 74 cb or near 0F 84 cd (synonym of JE)",
    "JNE": "Short 75 cb or near 0F 85 cd",
    "JNZ": "Short 75 cb or near 0F 85 cd (synonym of JNE)",
    "JG": "Short 7F cb or near 0F 8F cd",
    "JNLE": "Short 7F cb or near 0F 8F cd (synonym of JG)",
    "JGE": "Short 7D cb or near 0F 8D cd",
    "JNL": "Short 7D cb or near 0F 8D cd (synonym of JGE)",
    "JL": "Short 7C cb or near 0F 8C cd",
    "JNGE": "Short 7C cb or near 0F 8C cd (synonym of JL)",
    "JLE": "Short 7E cb or near 0F 8E cd",
    "JNG": "Short 7E cb or near 0F 8E cd (synonym of JLE)",
    "JA": "Short 77 cb or near 0F 87 cd",
    "JAE": "Short 73 cb or near 0F 83 cd",
    "JB": "Short 72 cb or near 0F 82 cd",
    "JBE": "Short 76 cb or near 0F 86 cd",
    "CALL": "Near relative E8 cd or indirect FF /2",
    "RET": "C3 (near return) or C2 iw (return with stack adjustment)",
    "NOP": "90",
    "LEA": "8D /r",
    "TEST": "Register/memory forms (e.g. 85 /r); immediate forms (F6 /0, F7 /0)",
    "NEG": "F6 /3 or F7 /3",
    "NOT": "F6 /2 or F7 /2",
    "SHL": "C0/C1 /4 or D0/D1 /4",
    "SAL": "Same encoding as SHL",
    "SHR": "C0/C1 /5 or D0/D1 /5",
    "SAR": "C0/C1 /7 or D0/D1 /7",
    "CLC": "F8",
    "STC": "F9",
    "CLD": "FC",
    "STD": "FD",
    "INT": "CD ib",
    "HLT": "F4",
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

    last_operand = "".join(current).strip()
    if last_operand:
        operands.append(last_operand)

    return operands

def classify_operand(operand):
    value = operand.strip()
    upper_value = value.upper()

    if upper_value in REGISTER_CODES:
        return "Register"
    if value.startswith("[") and value.endswith("]"):
        return "Memory"
    if re.fullmatch(r"[+-]?(?:\d+|0[xX][0-9A-Fa-f]+|[0-9A-Fa-f]+[Hh])", value):
        return "Immediate"
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return "Immediate"
    if value:
        return "Symbol"
    return "None"

def parse_label(statement):
    match = re.match(r"^([A-Za-z_.$?][A-Za-z0-9_.$?@]*):\s*(.*)$", statement)
    if match:
        return match.group(1), match.group(2).strip()
    return "", statement.strip()

def inspect_program(assembly_file):
    errors = []
    current_section = ""

    try:
        with open(assembly_file, "r", encoding="utf-8") as file:
            print("\nOPCODE AND REGISTER ENCODING LOOKUP")
            print("=" * 88)

            for line_number, raw_line in enumerate(file, start=1):
                statement = raw_line.split(";", 1)[0].strip()
                if not statement:
                    continue

                label, statement = parse_label(statement)
                if not statement:
                    if label:
                        print(f"Line {line_number}: label '{label}'")
                    continue

                parts = statement.split(None, 1)
                first_word = parts[0]
                upper_word = first_word.upper()
                operand_text = parts[1].strip() if len(parts) > 1 else ""

                if upper_word == "SECTION":
                    section_name = operand_text.lower()
                    if section_name in SECTIONS:
                        current_section = section_name
                    else:
                        print(f"Line {line_number}: unrecognized section '{operand_text}'")
                    continue

                if upper_word in SECTIONS:
                    current_section = upper_word.lower()
                    continue

                if upper_word in {"GLOBAL", "EXTERN", "BITS", "DEFAULT", "ALIGN", "SECTION"}:
                    continue

                if current_section in {".data", ".bss"}:
                    declaration_parts = statement.split(None, 2)
                    if len(declaration_parts) >= 2 and declaration_parts[1].upper() in DATA_DIRECTIVES:
                        continue
                    if upper_word in DATA_DIRECTIVES:
                        continue

                if upper_word in DATA_DIRECTIVES:
                    continue

                operands = split_operands(operand_text)
                print("-" * 88)
                print(f"Line       : {line_number}")
                if label:
                    print(f"Label      : {label}")
                print(f"Section    : {current_section or 'Unknown'}")
                print(f"Instruction: {statement}")
                print(f"Mnemonic   : {upper_word}")

                if upper_word not in OPCODE_FORMS:
                    print("Opcode form: Not available in this module")
                    errors.append(f"Line {line_number}: unsupported mnemonic '{upper_word}'.")
                else:
                    print(f"Opcode form: {OPCODE_FORMS[upper_word]}")

                if not operands:
                    print("Operands   : None")
                else:
                    for index, operand in enumerate(operands, start=1):
                        operand_type = classify_operand(operand)
                        print(f"Operand {index}: {operand} ({operand_type})")
                        register_code = REGISTER_CODES.get(operand.upper())
                        if register_code is not None:
                            print(
                                f"  Register encoding: {register_code} (binary), "
                                f"{int(register_code, 2)} (decimal)"
                            )

    except FileNotFoundError:
        print(f"Error: assembly file '{assembly_file}' was not found.")
        return
    except OSError as error:
        print(f"Error: could not read '{assembly_file}': {error}")
        return

    print("=" * 88)
    print("Register encoding table")
    print("-" * 44)
    print(f"{'Register':<12}{'Code (binary)':<18}{'Code (decimal)':<16}")
    for register, code in REGISTER_CODES.items():
        print(f"{register:<12}{code:<18}{int(code, 2):<16}")

    print("\nLookup completed.")
    if errors:
        print(f"Unsupported instructions found: {len(errors)}")
        for error in errors:
            print(error)
    else:
        print("No unsupported instruction mnemonics found.")

def main():
    if len(sys.argv) == 2:
        assembly_file = sys.argv[1]
    else:
        print("Opcode and Register Encoding Module")
        print("=" * 42)
        assembly_file = input("Enter assembly file name: ").strip()

    if not assembly_file:
        print("Error: assembly file name cannot be empty.")
        sys.exit(1)

    inspect_program(assembly_file)

if __name__ == "__main__":
    main()
