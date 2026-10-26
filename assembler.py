"""
Unified educational IA-32 assembler driver.

Run:
    python3 assembler.py fact.asm

This driver runs pass1.py first, then pass2.py verifies Pass 1 addresses/symbols
and generates machine code. Other project modules remain standalone utilities.
Output is a raw .text binary, not a linked executable/object file.
"""

import sys
from pathlib import Path
from pass2 import assemble


def main():
    if len(sys.argv) > 2:
        print("Usage: python3 assembler.py [source.asm]")
        sys.exit(2)

    if len(sys.argv) == 2:
        source_file = sys.argv[1]
    else:
        print("IA-32 EDUCATIONAL ASSEMBLER")
        print("=" * 42)
        source_file = input("Enter assembly file name (e.g. fact.asm): ").strip()

    if not source_file:
        print("Error: assembly file name cannot be empty.")
        sys.exit(2)

    if not Path(source_file).is_file():
        print(f"Error: source file '{source_file}' was not found.")
        sys.exit(1)

    try:
        assemble(source_file)
    except (ValueError, OSError) as error:
        print(f"Assembler error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
