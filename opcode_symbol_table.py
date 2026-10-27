
Opcode and Symbol Table Generator

Reads an assembly source file and displays:
- an opcode table with instruction examples and source line numbers
- a symbol table with addresses, sections, sizes, and values

The location counters are used to calculate the addresses of data and
supported instructions. This program reports reference opcode information;
it does not generate machine-code bytes.



import re
import sys
import ast
DATA = {'DB': 1, 'DW': 2, 'DD': 4}
RESERVE = {'RESB': 1, 'RESW': 2, 'RESD': 4}
SECTIONS = {'.text', '.data', '.bss'}
OPCODE_INFO = {'MOV': '88/89/8A/8B, B0-BF, C6/C7 (form-dependent)',
 'ADD': '00-05, 80/81/83 (form-dependent)',
 'SUB': '28-2D, 80/81/83 (form-dependent)',
 'MUL': 'F6/F7 /4',
 'IMUL': 'F6/F7 /5 or 0F AF',
 'DIV': 'F6/F7 /6',
 'IDIV': 'F6/F7 /7',
 'INC': 'FE/FF /0',
 'DEC': 'FE/FF /1',
 'CMP': '38-3D, 80/81/83 /7',
 'TEST': '84/85, F6/F7 /0',
 'AND': '20-25, 80/81/83 /4',
 'OR': '08-0D, 80/81/83 /1',
 'XOR': '30-35, 80/81/83 /6',
 'PUSH': '50-57, 68/6A, FF /6',
 'POP': '58-5F or 8F /0',
 'JMP': 'EB short, E9 near, FF /4',
 'JE': '74 short, 0F 84 near',
 'JZ': '74 short, 0F 84 near',
 'JNE': '75 short, 0F 85 near',
 'JNZ': '75 short, 0F 85 near',
 'JG': '7F short, 0F 8F near',
 'JGE': '7D short, 0F 8D near',
 'JL': '7C short, 0F 8C near',
 'JLE': '7E short, 0F 8E near',
 'JA': '77 short, 0F 87 near',
 'JAE': '73 short, 0F 83 near',
 'JB': '72 short, 0F 82 near',
 'JBE': '76 short, 0F 86 near',
 'CALL': 'E8 near, FF /2 indirect',
 'RET': 'C3 or C2 iw',
 'NOP': '90',
 'LEA': '8D /r',
 'INT': 'CD ib',
 'LOOP': 'E2 cb',
 'HLT': 'F4',
 'CLC': 'F8',
 'STC': 'F9',
 'CLD': 'FC',
 'STD': 'FD',
 'LEAVE': 'C9'}

# Convert decimal, hexadecimal (ending in h), and binary (ending in b) values.  


  def number(text):
    text = text.strip().lower()
    if text.endswith('h'):
        return int(text[:-1], 16)
    if text.endswith('b') and re.fullmatch('[01]+b', text):
        return int(text[:-1], 2)
    return int(text, 0)


def split_operands(text):
    result, current, depth, quote = ([], [], 0, None)
    for char in text:
        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
        if quote is None:
            if char == '[':
                depth += 1
            elif char == ']' and depth:
                depth -= 1
            elif char == ',' and depth == 0:
                result.append(''.join(current).strip())
                current = []
                continue
        current.append(char)
    last = ''.join(current).strip()
    if last:
        result.append(last)
    return result

def data_size(directive, text):
    values, current, quote = ([], [], None)
    for char in text:
        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
        if char == ',' and quote is None:
            values.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
    values.append(''.join(current).strip())
    if quote or any((not v for v in values)):
        raise ValueError('Invalid data value list.')
    total, shown = (0, [])
    for item in values:
        if item.startswith(("'", '"')):
            if directive != 'DB':
                raise ValueError('Quoted strings are only supported with DB.')
            value = ast.literal_eval(item)
            if not isinstance(value, str):
                raise ValueError('Invalid string value.')
            total += len(value.encode('ascii'))
            shown.append(value)
        else:
            n = number(item)
            bits = DATA[directive] * 8
            if n < -2 ** (bits - 1) or n > 2 ** bits - 1:
                raise ValueError(f'Value {item} does not fit in {bits} bits.')
            total += DATA[directive]
            shown.append(item)
    return (total, ', '.join(shown))

def reg_size(op):
    op = op.upper()
    if op in {'AL', 'CL', 'DL', 'BL', 'AH', 'CH', 'DH', 'BH'}:
        return 1
    if op in {'AX', 'CX', 'DX', 'BX', 'SP', 'BP', 'SI', 'DI'}:
        return 2
    if op in {'EAX', 'ECX', 'EDX', 'EBX', 'ESP', 'EBP', 'ESI', 'EDI'}:
        return 4
    return 0

def instruction_size(mnemonic, text):
    ops = split_operands(text)
    m = mnemonic.upper()
    if m in {'NOP', 'RET', 'LEAVE', 'HLT', 'CLC', 'STC', 'CLD', 'STD'} and (not ops):
        return 1
    if m in {'PUSH', 'POP'} and len(ops) == 1:
        if reg_size(ops[0]) == 4:
            return 1
        if reg_size(ops[0]) == 2:
            return 2
        if m == 'PUSH':
            try:
                return 2 if -128 <= number(ops[0]) <= 127 else 5
            except ValueError:
                pass
    if m in {'INC', 'DEC'} and len(ops) == 1 and reg_size(ops[0]):
        return 1 if reg_size(ops[0]) == 4 else 2
    if m == 'MUL' and len(ops) == 1:
        if reg_size(ops[0]) in {1, 4}:
            return 2
        if reg_size(ops[0]) == 2:
            return 3
        if ops[0].startswith('['):
            return 6
    if m in {'CALL', 'JMP'} and len(ops) == 1:
        return 5
    if m in {'JE', 'JZ', 'JNE', 'JNZ', 'JG', 'JGE', 'JL', 'JLE', 'JA', 'JAE', 'JB', 'JBE', 'JO', 'JNO', 'JS', 'JNS', 'JP', 'JNP'} and len(ops) == 1:
        return 6
    if m == 'LOOP' and len(ops) == 1:
        return 2
    if m == 'INT' and len(ops) == 1:
        return 2
    if len(ops) == 2:
        a, b = (ops[0].upper(), ops[1].upper())
        sa, sb = (reg_size(a), reg_size(b))
        if m in {'MOV', 'ADD', 'SUB', 'XOR', 'AND', 'OR', 'CMP', 'TEST'} and sa and sb:
            if sa != sb:
                raise ValueError('Register operands must have matching sizes.')
            return 2 if sa in {1, 4} else 3
        if m in {'MOV', 'ADD', 'SUB', 'XOR', 'AND', 'OR', 'CMP'} and sa:
            try:
                n = number(ops[1])
                if m == 'MOV':
                    return 2 + sa
                return 3 if -128 <= n <= 127 else 2 + sa
            except ValueError:
                pass
        if a.startswith('[') and sb:
            return 6 if sb == 4 else 5
        if sa and b.startswith('['):
            return 6 if sa == 4 else 5
    raise ValueError(f'Unsupported instruction or operand format: {m} {text}'.strip())

def process_file(filename):
    try:
        with open(filename, encoding='utf-8') as file:
            lines = [(i, raw.split(';', 1)[0].strip()) for i, raw in enumerate(file, 1) if raw.split(';', 1)[0].strip()]
    except FileNotFoundError:
        print(f"Error: assembly file '{filename}' was not found.")
        return
    except OSError as error:
        print(f'Error: could not read file: {error}')
        return
    symbols, opcodes, errors = ({}, {}, [])
    offsets = {'.data': 0, '.bss': 0, '.text': 0}
    section = None
    for line_no, original in lines:
        statement = original
        sm = re.match('^(?:SECTION\\s+)?(\\.(?:DATA|BSS|TEXT))\\s*$', statement, re.I)
        if sm:
            section = sm.group(1).lower()
            continue
        if statement.lower().startswith(('global ', 'extern ', 'bits ')):
            continue
        lm = re.match('^([A-Za-z_.$?][A-Za-z0-9_.$?@]*):\\s*(.*)$', statement)
        if lm:
            label, statement = (lm.group(1), lm.group(2).strip())
            if section == '.text':
                symbols[label] = {'address': offsets['.text'], 'section': '.text', 'size': 'Label', 'value': f"{offsets['.text']:08X}", 'line': line_no}
            if not statement:
                continue
        if section in {'.data', '.bss'}:
            parts = statement.split(None, 2)
            if len(parts) >= 2 and parts[1].upper() in DATA | RESERVE:
                name, directive = (parts[0], parts[1].upper())
                value = parts[2].strip() if len(parts) > 2 else ''
                try:
                    if directive in DATA:
                        if section != '.data':
                            raise ValueError(f'{directive} belongs in .data.')
                        if not value:
                            raise ValueError('Missing initialization value.')
                        size, shown = data_size(directive, value)
                    else:
                        if section != '.bss':
                            raise ValueError(f'{directive} belongs in .bss.')
                        count = number(value)
                        if count <= 0:
                            raise ValueError('Reservation size must be positive.')
                        size = count * RESERVE[directive]
                        shown = 'Uninitialized'
                    if name in symbols:
                        raise ValueError(f"Duplicate symbol '{name}'.")
                    symbols[name] = {'address': offsets[section], 'section': section, 'size': size, 'value': shown, 'line': line_no}
                    offsets[section] += size
                except (ValueError, SyntaxError, UnicodeEncodeError) as error:
                    errors.append(f'Line {line_no}: {error}')
            continue
        if section == '.text' and statement:
            parts = statement.split(None, 1)
            mnemonic = parts[0].upper()
            operand = parts[1] if len(parts) > 1 else ''
            if mnemonic not in opcodes:
                opcodes[mnemonic] = {'example': operand, 'lines': [line_no]}
            else:
                opcodes[mnemonic]['lines'].append(line_no)
    offsets['.text'] = 0
    section = None
    for line_no, original in lines:
        statement = original
        sm = re.match('^(?:SECTION\\s+)?(\\.(?:DATA|BSS|TEXT))\\s*$', statement, re.I)
        if sm:
            section = sm.group(1).lower()
            continue
        if statement.lower().startswith(('global ', 'extern ', 'bits ')):
            continue
        if section != '.text':
            continue
        lm = re.match('^([A-Za-z_.$?][A-Za-z0-9_.$?@]*):\\s*(.*)$', statement)
        if lm:
            label, statement = (lm.group(1), lm.group(2).strip())
            symbols[label] = {'address': offsets['.text'], 'section': '.text', 'size': 'Label', 'value': f"{offsets['.text']:08X}", 'line': line_no}
            if not statement:
                continue
        if not statement:
            continue
        parts = statement.split(None, 1)
        mnemonic = parts[0].upper()
        operand = parts[1] if len(parts) > 1 else ''
        try:
            offsets['.text'] += instruction_size(mnemonic, operand)
        except (ValueError, TypeError) as error:
            errors.append(f'Line {line_no}: {error}')
    print('\n' + '=' * 100 + '\nOPCODE TABLE\n' + '=' * 100)
    print(f"{'Mnemonic':<12}{'Opcode information':<48}{'Example operands':<24}{'Source lines'}")
    print('-' * 100)
    for mnemonic, info in opcodes.items():
        print(f"{mnemonic:<12}{OPCODE_INFO.get(mnemonic, 'Not in reference list'):<48}{info['example'][:22]:<24}{', '.join(map(str, info['lines']))}")
    print('-' * 100 + f'\nUnique mnemonics: {len(opcodes)}')
    print('\n' + '=' * 100 + '\nSYMBOL TABLE\n' + '=' * 100)
    print(f"{'Symbol Name':<18}{'Symbol Address':<20}{'Section':<12}{'Symbol Size':<16}Value")
    print('-' * 100)
    for name, info in symbols.items():
        size = info['size'] if isinstance(info['size'], str) else f"{info['size']} byte(s)"
        print(f"{name:<18}{info['address']:08X}{'':<12}{info['section']:<12}{str(size):<16}{info['value']}")
    print('-' * 100 + f'\nTotal symbols: {len(symbols)}')
    if errors:
        print('\nErrors:')
        for error in errors:
            print(error)
    else:
        print('\nBoth tables generated successfully.')
    print('Note: opcode entries are reference descriptions; machine-code bytes are not generated.')

def main():
    if len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        print('Combined Opcode and Symbol Table Generator')
        filename = input('Enter assembly file name: ').strip()
    if not filename:
        print('Error: assembly file name cannot be empty.')
        sys.exit(1)
    process_file(filename)
if __name__ == '__main__':
    main()
