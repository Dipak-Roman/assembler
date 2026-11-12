import re
import sys


def split_arguments(text):
    text = text.strip()
    if not text:
        return []
    if "," in text:
        return [item.strip() for item in text.split(",")]
    return text.split()


def read_source(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return file.readlines()


def build_tables(lines):
    mnt = []
    mdt = []
    macros = {}
    inside_macro = False
    current_macro = None

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if stripped.startswith("%macro"):
            parts = stripped.split()
            if len(parts) != 3:
                raise ValueError(f"Invalid macro definition at line {line_number}")

            macro_name = parts[1]
            try:
                parameter_count = int(parts[2])
            except ValueError:
                raise ValueError(f"Invalid parameter count at line {line_number}")

            if macro_name in macros:
                raise ValueError(f"Duplicate macro definition: {macro_name}")

            current_macro = {
                "name": macro_name,
                "parameter_count": parameter_count,
                "mdtp": len(mdt) + 1,
                "body": []
            }
            inside_macro = True
            continue

        if stripped.startswith("%endmacro"):
            if not inside_macro:
                raise ValueError(f"%endmacro without %macro at line {line_number}")

            mdt.append("MEND")
            macros[current_macro["name"]] = current_macro
            mnt.append({
                "index": len(mnt) + 1,
                "name": current_macro["name"],
                "parameter_count": current_macro["parameter_count"],
                "mdtp": current_macro["mdtp"]
            })
            current_macro = None
            inside_macro = False
            continue

        if inside_macro:
            current_macro["body"].append(line.rstrip("\n"))
            mdt.append(line.rstrip("\n"))

    if inside_macro:
        raise ValueError("Macro definition is missing %endmacro")

    return mnt, mdt, macros


def expand_macro(body, arguments):
    expanded_lines = []

    for line in body:
        expanded = re.sub(
            r"%([1-9][0-9]*)",
            lambda match: arguments[int(match.group(1)) - 1]
            if int(match.group(1)) <= len(arguments)
            else match.group(0),
            line
        )
        expanded_lines.append(expanded)

    return expanded_lines


def expand_source(lines, macros):
    output = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped.startswith("%macro"):
            while index < len(lines) and not lines[index].strip().startswith("%endmacro"):
                index += 1
            index += 1
            continue

        parts = stripped.split(None, 1)

        if parts and parts[0] in macros:
            macro = macros[parts[0]]
            argument_text = parts[1] if len(parts) > 1 else ""
            arguments = split_arguments(argument_text)

            if len(arguments) != macro["parameter_count"]:
                raise ValueError(
                    f"Macro {macro['name']} expects {macro['parameter_count']} "
                    f"arguments but received {len(arguments)}"
                )

            output.extend(expand_macro(macro["body"], arguments))
        else:
            output.append(line.rstrip("\n"))

        index += 1

    return output


def display_mnt(mnt):
    print("\nMNT - MACRO NAME TABLE")
    print("-" * 58)
    print(f"{'Index':<10}{'Macro Name':<20}{'PP':<10}{'MDTP':<10}")
    print("-" * 58)

    for entry in mnt:
        print(
            f"{entry['index']:<10}"
            f"{entry['name']:<20}"
            f"{entry['parameter_count']:<10}"
            f"{entry['mdtp']:<10}"
        )


def display_mdt(mdt):
    print("\nMDT - MACRO DEFINITION TABLE")
    print("-" * 58)
    print(f"{'Index':<10}Definition")
    print("-" * 58)

    for index, definition in enumerate(mdt, start=1):
        print(f"{index:<10}{definition}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 macro_processor.py input.asm")
        return 1

    filename = sys.argv[1]

    try:
        lines = read_source(filename)
        mnt, mdt, macros = build_tables(lines)
        expanded_output = expand_source(lines, macros)

        display_mnt(mnt)
        display_mdt(mdt)

        print("\nEXPANDED SOURCE CODE")
        print("-" * 58)

        for line in expanded_output:
            print(line)

    except FileNotFoundError:
        print("File not found:", filename)
        return 1
    except (OSError, ValueError) as error:
        print("Error:", error)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
