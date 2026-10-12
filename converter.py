from pathlib import Path
import sys
import re


def ascii_to_hex(value):
    """Convert an ASCII string into hexadecimal."""
    hex_values = []

    for char in value:
        hex_values.append(f"{ord(char):02X}")

    return " ".join(hex_values)


def convert_db_value(value):
    """Convert DB value into ASCII and hexadecimal."""
    value = value.strip()

    # Handle quoted strings
    if (value.startswith("'") and value.endswith("'")) or \
       (value.startswith('"') and value.endswith('"')):

        text = value[1:-1]

        ascii_value = text
        hex_value = ascii_to_hex(text)

        return ascii_value, hex_value

    
    parts = value.split(",")

    ascii_values = []
    hex_values = []

    for part in parts:
        part = part.strip()

        try:
            number = int(part, 0)
            ascii_values.append(chr(number))
            hex_values.append(f"{number:02X}")

        except ValueError:
            ascii_values.append(part)
            hex_values.append(ascii_to_hex(part))

    return "".join(ascii_values), " ".join(hex_values)


def convert_dd_value(value):
    """Convert DD numeric value directly into hexadecimal."""
    value = value.strip()

    try:
        number = int(value, 0)
        return f"{number:08X}"

    except ValueError:
        return "Invalid value"


def inspect_data_section(assembly_file):
    """Read the ASM file and convert DB and DD values."""

    in_data_section = False

    try:
        with open(assembly_file, "r", encoding="utf-8") as file:

            for line_number, raw_line in enumerate(file, start=1):

                
                statement = raw_line.split(";", 1)[0].strip()

                if not statement:
                    continue

                
                if statement.lower() in [".data", "section .data"]:
                    in_data_section = True

                    print("\n" + "=" * 52)
                    print("DATA SECTION")
                    print("=" * 52)

                    continue

                
                if statement.lower().startswith("section ") and \
                   statement.lower() != "section .data":
                    in_data_section = False
                    continue

                if not in_data_section:
                    continue

                
                parts = statement.split(None, 2)

                if len(parts) < 3:
                    continue

                variable_name = parts[0]
                data_type = parts[1].upper()
                value = parts[2].strip()

                if data_type not in ["DB", "DD"]:
                    continue

                print("\n" + "-" * 52)
                print(f"Line {line_number}: {statement}")
                print(f"Variable  : {variable_name}")
                print(f"Type      : {data_type}")
                print(f"Value     : {value}")

                if data_type == "DB":

                    ascii_value, hex_value = convert_db_value(value)

                    print(f"ASCII     : {ascii_value}")
                    print(f"Hex       : {hex_value}")

                elif data_type == "DD":

                    hex_value = convert_dd_value(value)

                    print(f"Hex       : {hex_value}")

    except FileNotFoundError:
        print(f"Error: assembly file '{assembly_file}' was not found.")
        sys.exit(1)


def main():

    if len(sys.argv) == 2:
        assembly_file = sys.argv[1]

    else:
        print("ASM Data Converter")
        print("=" * 52)

        assembly_file = input(
            "Enter assembly file name: "
        ).strip()

    inspect_data_section(assembly_file)

    print("\n" + "=" * 52)
    print("Conversion completed.")


if __name__ == "__main__":
    main()
