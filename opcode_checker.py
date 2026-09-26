from pathlib import Path
import sys
import re

REGISTERS = {
    "EAX", "EBX", "ECX", "EDX",
    "ESI", "EDI", "ESP", "EBP"
}


def load_opcode_table(filename):
    """Read the opcode file and keep the supported mnemonics."""
    mnemonics = set()

    try:
        with open(filename, "r", encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()

                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if parts:
                    mnemonics.add(parts[0].upper())

    except FileNotFoundError:
        print(f"Error: opcode file '{filename}' was not found.")
        sys.exit(1)

    return mnemonics


def classify_operand(value):
    """Return the type of an assembly operand."""
    value = value.strip()
    upper_value = value.upper()

    if upper_value in REGISTERS:
        return "Register"

    if value.startswith("[") and value.endswith("]"):
        return "Memory"

    # Decimal integer, including +25 and -10
    if re.fullmatch(r"[+-]?\d+", value):
        return "Constant"

    return "Symbol"


def split_operands(text):
    """Split operands at commas, but not commas inside [ ]."""
    if not text.strip():
        return []

    result = []
    current = []
    square_brackets = 0

    for char in text:
        if char == "[":
            square_brackets += 1
        elif char == "]" and square_brackets:
            square_brackets -= 1

        if char == "," and square_brackets == 0:
            result.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    last = "".join(current).strip()
    if last:
        result.append(last)

    return result


def inspect_program(assembly_file, opcode_set):
    try:
        with open(assembly_file, "r", encoding="utf-8") as file:
            for line_number, raw_line in enumerate(file, start=1):
                # Ignore comments after ';'
                statement = raw_line.split(";", 1)[0].strip()

                if not statement:
                    continue

                parts = statement.split(None, 1)
                mnemonic = parts[0].upper()
                operand_text = parts[1] if len(parts) == 2 else ""

                operands = split_operands(operand_text)
                found = mnemonic in opcode_set

                print("\n" + "-" * 52)
                print(f"Line {line_number}: {statement}")
                print(f"Mnemonic : {mnemonic}")
                print(f"In table : {'YES' if found else 'NO'}")

                if not operands:
                    print("Operands : None")
                    print("Types    : None")
                    continue

                for number, operand in enumerate(operands, start=1):
                    print(f"Operand {number} : {operand}")
                    print(f"Type     : {classify_operand(operand)}")

    except FileNotFoundError:
        print(f"Error: assembly file '{assembly_file}' was not found.")
        sys.exit(1)


def main():
    if len(sys.argv) == 3:
        opcode_file = sys.argv[1]
        assembly_file = sys.argv[2]
    else:
        print("Opcode Checker")
        print("=" * 52)
        opcode_file = input("Enter opcode file name: ").strip()
        assembly_file = input("Enter assembly file name: ").strip()

    opcode_set = load_opcode_table(opcode_file)

    print(f"\nLoaded {len(opcode_set)} unique mnemonics.")
    inspect_program(assembly_file, opcode_set)

    print("\n" + "=" * 52)
    print("Opcode checking completed.")


if __name__ == "__main__":
    main()
