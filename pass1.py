import re
import sys

REGISTERS = {'EAX', 'ECX', 'EDX', 'EBX', 'ESP', 'EBP', 'ESI', 'EDI'}
DATA_SIZES = {'DB': 1, 'DW': 2, 'DD': 4}
RESERVE_SIZES = {'RESB': 1, 'RESW': 2, 'RESD': 4}
JUMPS = {'JE', 'JNE', 'JG', 'JGE', 'JL', 'JLE', 'JA', 'JAE', 'JB', 'JBE', 'JZ', 'JNZ'}


def split_values(text):
    values, current, quote = [], '', None
    for char in text:
        if char in "'\"":
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
        if char == ',' and quote is None:
            values.append(current.strip())
            current = ''
        else:
            current += char
    values.append(current.strip())
    if quote or any(not item for item in values):
        raise ValueError('Invalid or unclosed data value.')
    return values


def number(text):
    text = text.strip()
    if text.lower().endswith('h'):
        return int(text[:-1], 16)
    return int(text, 0) if text.lower().startswith(('0x', '0b')) else int(text, 10)


def data_size(directive, text):
    if directive in RESERVE_SIZES:
        count = number(text)
        if count < 0:
            raise ValueError('Reservation count cannot be negative.')
        return count * RESERVE_SIZES[directive]
    total = 0
    for value in split_values(text):
        if value.startswith(("'", '"')):
            if not value.endswith(value[0]) or directive != 'DB':
                raise ValueError('Quoted strings are supported only for DB.')
            total += len(value[1:-1].encode('ascii'))
        else:
            number(value)
            total += DATA_SIZES[directive]
    return total


def instruction_size(mnemonic, operands):
    operands = [re.sub(r'^(BYTE|WORD|DWORD)\s*', '', x.strip(), flags=re.I).strip() for x in operands]
    if mnemonic in {'NOP', 'RET', 'HLT'} and not operands:
        return 1
    if mnemonic in {'MUL', 'DIV', 'NEG', 'NOT'} and len(operands) == 1 and operands[0].upper() in REGISTERS:
        return 2
    if mnemonic in {'INC', 'DEC', 'PUSH', 'POP'} and len(operands) == 1 and operands[0].upper() in REGISTERS:
        return 1
    if mnemonic == 'INT' and len(operands) == 1:
        if not 0 <= number(operands[0]) <= 255:
            raise ValueError('INT number must fit in one byte.')
        return 2
    if mnemonic in JUMPS and len(operands) == 1:
        return 6  # Fixed near conditional jump encoding.
    if mnemonic in {'JMP', 'CALL'} and len(operands) == 1:
        return 5  # Fixed near relative encoding.
    if len(operands) == 2:
        dst, src = [x.upper() for x in operands]
        if mnemonic == 'MOV' and dst in REGISTERS:
            if src in REGISTERS:
                return 2
            if src.startswith('[') and src.endswith(']'):
                return 6  # Absolute [symbol] with disp32 only.
            number(src)
            return 5  # B8+rd imm32.
        if mnemonic == 'MOV' and dst.startswith('[') and dst.endswith(']') and src in REGISTERS:
            return 6  # Absolute [symbol] with disp32 only.
        if mnemonic in {'ADD', 'SUB', 'CMP', 'AND', 'OR', 'XOR'} and dst in REGISTERS:
            if src in REGISTERS:
                return 2
            value = number(src)
            return 3 if -128 <= value <= 127 else 6
    raise ValueError(f'Unsupported instruction or operand format: {mnemonic} {", ".join(operands)}')


def pass_one(filename):
    offsets = {'.data': 0, '.bss': 0, '.text': 0}
    symbols, intermediate, errors = {}, [], []
    section = None
    try:
        with open(filename, encoding='utf-8') as file:
            lines = list(enumerate(file, 1))
    except OSError as error:
        print(f'Error reading {filename}: {error}')
        return

    for line_no, raw in lines:
        statement = raw.split(';', 1)[0].strip()
        if not statement:
            continue
        section_match = re.fullmatch(r'(?:section\s+)?(\.data|\.bss|\.text)', statement, re.I)
        if section_match:
            section = section_match.group(1).lower()
            continue
        if statement.lower().startswith(('global ', 'extern ', 'bits ')):
            continue
        label_match = re.match(r'^([A-Za-z_.$?][\w.$?@]*):\s*(.*)$', statement)
        if label_match:
            label, statement = label_match.groups()
            key = label.upper()
            if key in symbols:
                errors.append(f'Line {line_no}: Duplicate symbol {label}.')
            elif section != '.text':
                errors.append(f'Line {line_no}: Label outside .text section.')
            else:
                symbols[key] = (label, offsets['.text'], '.text', 'Label')
            if not statement:
                continue
        if section not in offsets:
            errors.append(f'Line {line_no}: Statement outside a section.')
            continue
        try:
            if section in {'.data', '.bss'}:
                parts = statement.split(None, 2)
                if len(parts) != 3:
                    raise ValueError('Expected name, directive, and value/count.')
                name, directive, value = parts
                directive = directive.upper()
                if directive not in DATA_SIZES and directive not in RESERVE_SIZES:
                    raise ValueError(f'Unsupported directive {directive}.')
                if section == '.data' and directive in RESERVE_SIZES or section == '.bss' and directive in DATA_SIZES:
                    raise ValueError(f'{directive} is not valid in {section}.')
                size = data_size(directive, value)
                key = name.upper()
                if key in symbols:
                    raise ValueError(f'Duplicate symbol {name}.')
                symbols[key] = (name, offsets[section], section, size)
            else:
                parts = statement.split(None, 1)
                directive = parts[0].upper()
                value = parts[1] if len(parts) > 1 else ''
                operands = split_values(value) if value else []
                size = instruction_size(directive, operands)
            intermediate.append((line_no, section, offsets[section], size, statement))
            offsets[section] += size
        except (ValueError, UnicodeError) as error:
            errors.append(f'Line {line_no}: {error}')

    if errors:
        print('\nPASS 1 ERRORS - TABLES NOT GENERATED')
        for error in errors:
            print(error)
        return

    print('\nPASS 1 - SYMBOL TABLE')
    print('=' * 76)
    print(f'{"Symbol":<18}{"Address":<14}{"Section":<12}{"Size":<12}')
    for name, address, sec, size in symbols.values():
        print(f'{name:<18}{address:08X}      {sec:<12}{str(size):<12}')
    print('\nPASS 1 - INTERMEDIATE ADDRESS TABLE')
    print('=' * 90)
    print(f'{"Line":<8}{"Section":<12}{"Address":<14}{"Size":<8}Statement')
    for line_no, sec, address, size, statement in intermediate:
        print(f'{line_no:<8}{sec:<12}{address:08X}      {size:<8}{statement}')
    print('\nSection sizes:', ', '.join(f'{sec}={size} bytes' for sec, size in offsets.items()))
    print('Pass 1 completed. Addresses are section-relative; branch sizes use fixed near forms.')


def main():
    filename = sys.argv[1] if len(sys.argv) == 2 else input('Enter assembly file name: ').strip()
    if not filename:
        print('Error: File name cannot be empty.')
        return
    pass_one(filename)


if __name__ == '__main__':
    main()
