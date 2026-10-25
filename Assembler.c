#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>

#define MAX_LINE    512
#define MAX_ITEMS   64
#define MAX_ITEM    128
#define MAX_BYTES   2048
#define MAX_OPCODES 100
#define MAX_SYMBOLS 100
#define MAX_GLOBALS 20
#define NAME_SIZE   32
#define SECTION_SIZE 40

struct Opcode
{
    char opcode[8];
    char mnemonic[16];
    int  operandCount;
    char type1[8];
    char type2[8];
    char modrm[4];
    int  ext;
};

struct DataLine
{
    char name[NAME_SIZE];
    char type[4];
    char items[MAX_ITEMS][MAX_ITEM];
    int  itemCount;
};

struct Symbol
{
    char name[NAME_SIZE];
    long offset;
    int  hasOffset;
    int  size;
    char type;
};

struct Opcode table[MAX_OPCODES];
int tableCount = 0;

struct Symbol symbols[MAX_SYMBOLS];
int symbolCount = 0;

char globalNames[MAX_GLOBALS][NAME_SIZE];
int  globalCount = 0;

int lineNumber = 0;

void Trim(char *str)
{
    int start = 0;
    int end = (int)strlen(str) - 1;

    while (str[start] != '\0' && isspace((unsigned char)str[start]))
        start++;

    while (end >= start && isspace((unsigned char)str[end]))
    {
        str[end] = '\0';
        end--;
    }

    if (start > 0)
        memmove(str, str + start, strlen(str + start) + 1);
}

void ToLower(char *str)
{
    int i;
    for (i = 0; str[i] != '\0'; i++)
        str[i] = (char)tolower((unsigned char)str[i]);
}

void RemoveComment(char *line)
{
    int i;
    char quote = 0;

    for (i = 0; line[i] != '\0'; i++)
    {
        if (quote != 0)
        {
            if (line[i] == quote)
                quote = 0;
        }
        else if (line[i] == '\'' || line[i] == '"')
        {
            quote = line[i];
        }
        else if (line[i] == ';')
        {
            line[i] = '\0';
            return;
        }
    }
}

int ReadLine(FILE *fp, char *line)
{
    int c;

    if (fgets(line, MAX_LINE, fp) == NULL)
        return 0;

    lineNumber++;

    if (strchr(line, '\n') == NULL && !feof(fp))
    {
        printf("Warning line %d: line too long, extra text ignored\n", lineNumber);
        while ((c = fgetc(fp)) != '\n' && c != EOF)
            ;
    }

    RemoveComment(line);
    Trim(line);
    return 1;
}

char *GetWord(char *line, char *word, int size)
{
    int n = 0;

    while (*line != '\0' && isspace((unsigned char)*line))
        line++;

    while (*line != '\0' && !isspace((unsigned char)*line))
    {
        if (n < size - 1)
        {
            word[n] = *line;
            n++;
        }
        line++;
    }
    word[n] = '\0';

    while (*line != '\0' && isspace((unsigned char)*line))
        line++;

    return line;
}

int IsQuoted(char *str)
{
    int len = (int)strlen(str);

    if (len >= 2 && (str[0] == '\'' || str[0] == '"') && str[len - 1] == str[0])
        return 1;
    return 0;
}

int GetNumber(char *str, long *value)
{
    char *end;

    if (str[0] == '\0')
        return 0;

    errno = 0;
    if (str[0] == '0' && (str[1] == 'x' || str[1] == 'X'))
        *value = strtol(str, &end, 16);
    else
        *value = strtol(str, &end, 10);

    if (*end != '\0' || errno == ERANGE)
        return 0;
    return 1;
}

int SplitValues(char *text, char items[][MAX_ITEM])
{
    int count = 0;
    int n = 0;
    int i;
    int tooLong = 0;
    char quote = 0;
    char current[MAX_ITEM];

    for (i = 0; ; i++)
    {
        char c = text[i];

        if (c == '\0' || (quote == 0 && c == ','))
        {
            current[n] = '\0';
            Trim(current);

            if (tooLong)
            {
                printf("Error line %d: a value is longer than %d characters\n",
                       lineNumber, MAX_ITEM - 1);
                return -1;
            }
            if (current[0] != '\0')
            {
                if (count >= MAX_ITEMS)
                {
                    printf("Error line %d: more than %d values\n",
                           lineNumber, MAX_ITEMS);
                    return -1;
                }
                strcpy(items[count], current);
                count++;
            }
            n = 0;

            if (c == '\0')
                break;
            continue;
        }

        if (quote != 0)
        {
            if (c == quote)
                quote = 0;
        }
        else if (c == '\'' || c == '"')
        {
            quote = c;
        }

        if (n < MAX_ITEM - 1)
        {
            current[n] = c;
            n++;
        }
        else
        {
            tooLong = 1;
        }
    }
    return count;
}

int IsSectionLine(char *line, char *section)
{
    char word1[NAME_SIZE], word2[NAME_SIZE];
    char *rest;

    rest = GetWord(line, word1, sizeof(word1));
    ToLower(word1);

    if (strcmp(word1, "section") == 0 || strcmp(word1, "segment") == 0)
    {
        GetWord(rest, word2, sizeof(word2));
        ToLower(word2);

        if (word2[0] == '.')
            snprintf(section, SECTION_SIZE, "%s", word2);
        else
            snprintf(section, SECTION_SIZE, ".%s", word2);
        return 1;
    }

    if (strcmp(word1, ".data") == 0 || strcmp(word1, ".text") == 0 ||
        strcmp(word1, ".bss") == 0)
    {
        snprintf(section, SECTION_SIZE, "%s", word1);
        return 1;
    }
    return 0;
}

int IsGlobalLine(char *line, char *names, int size)
{
    char word1[NAME_SIZE];
    char *rest;

    rest = GetWord(line, word1, sizeof(word1));
    ToLower(word1);

    if (strcmp(word1, "global") == 0)
    {
        snprintf(names, size, "%s", rest);
        return 1;
    }
    return 0;
}

int IsDirective(char *line)
{
    char word[NAME_SIZE];

    GetWord(line, word, sizeof(word));
    ToLower(word);

    if (strcmp(word, "global") == 0 || strcmp(word, "extern") == 0 ||
        strcmp(word, "bits") == 0   || strcmp(word, "default") == 0)
        return 1;
    return 0;
}

int IsLabelLine(char *line, char *label, char **rest)
{
    char word[NAME_SIZE];
    char *after;
    int len;

    *rest = line;
    after = GetWord(line, word, sizeof(word));
    len = (int)strlen(word);

    if (len > 1 && word[len - 1] == ':')
    {
        word[len - 1] = '\0';
        strcpy(label, word);
        *rest = after;
        return 1;
    }
    return 0;
}

int ParseDataLine(char *line, struct DataLine *d)
{
    char name[NAME_SIZE], type[16];
    char *rest;
    int len;

    rest = GetWord(line, name, sizeof(name));
    rest = GetWord(rest, type, sizeof(type));
    ToLower(type);

    if (strcmp(type, "db") != 0 && strcmp(type, "dd") != 0)
        return 0;

    if (*rest == '\0')
    {
        printf("Error line %d: %s has no value\n", lineNumber, name);
        return -1;
    }

    len = (int)strlen(name);
    if (len > 0 && name[len - 1] == ':')
        name[len - 1] = '\0';
    if (len >= NAME_SIZE - 1)
        printf("Warning line %d: name is too long, shortened to %d characters\n",
               lineNumber, NAME_SIZE - 1);

    strcpy(d->name, name);
    strcpy(d->type, type);
    d->itemCount = SplitValues(rest, d->items);

    if (d->itemCount < 0)
        return -1;
    if (d->itemCount == 0)
    {
        printf("Error line %d: %s has no value\n", lineNumber, name);
        return -1;
    }
    return 1;
}

int MakeBytes(char *type, char *item, unsigned char *out, int max)
{
    long value;
    int i, len;

    if (IsQuoted(item))
    {
        if (strcmp(type, "dd") == 0)
            return -1;

        len = (int)strlen(item) - 2;
        if (len > max)
            return -1;
        for (i = 0; i < len; i++)
            out[i] = (unsigned char)item[i + 1];
        return len;
    }

    if (GetNumber(item, &value) == 0)
        return -1;

    if (strcmp(type, "dd") == 0)
    {
        if (max < 4 || value < -2147483647L - 1 || value > 4294967295L)
            return -1;
        out[0] = (unsigned char)(value & 0xFF);
        out[1] = (unsigned char)((value >> 8) & 0xFF);
        out[2] = (unsigned char)((value >> 16) & 0xFF);
        out[3] = (unsigned char)((value >> 24) & 0xFF);
        return 4;
    }

    if (max < 1 || value < -128 || value > 255)
        return -1;
    out[0] = (unsigned char)(value & 0xFF);
    return 1;
}

int MakeAllBytes(struct DataLine *d, unsigned char *out)
{
    int i, n, total = 0;

    for (i = 0; i < d->itemCount; i++)
    {
        n = MakeBytes(d->type, d->items[i], out + total, MAX_BYTES - total);
        if (n < 0)
        {
            printf("Error line %d: bad value '%s' in %s\n",
                   lineNumber, d->items[i], d->name);
            return -1;
        }
        total = total + n;
    }
    return total;
}

void PrintItems(struct DataLine *d)
{
    int i;
    for (i = 0; i < d->itemCount; i++)
    {
        printf("%s", d->items[i]);
        if (i < d->itemCount - 1)
            printf(",");
    }
}

int IsRegister(char *op)
{
    char *regs[] = { "eax", "ebx", "ecx", "edx", "esi", "edi", "esp", "ebp",
                     "ax", "bx", "cx", "dx", "si", "di", "sp", "bp",
                     "al", "ah", "bl", "bh", "cl", "ch", "dl", "dh", NULL };
    char copy[MAX_ITEM];
    int i;

    snprintf(copy, sizeof(copy), "%s", op);
    ToLower(copy);

    for (i = 0; regs[i] != NULL; i++)
        if (strcmp(copy, regs[i]) == 0)
            return 1;
    return 0;
}

char *OperandType(char *op)
{
    long value;

    if (IsRegister(op))
        return "reg";
    if (op[0] == '[')
        return "mem";
    if (GetNumber(op, &value) || IsQuoted(op))
        return "imm";
    return "sym";
}

int LoadOpcodeTable(char *fileName)
{
    FILE *fp;
    char line[MAX_LINE];
    char countText[8], extText[8];
    char *rest;
    long count, ext;
    struct Opcode *row;

    tableCount = 0;
    lineNumber = 0;

    fp = fopen(fileName, "r");
    if (fp == NULL)
        return 0;

    while (ReadLine(fp, line))
    {
        if (line[0] == '\0')
            continue;

        if (tableCount >= MAX_OPCODES)
        {
            printf("Warning: opcode table full, extra rows ignored\n");
            break;
        }

        row = &table[tableCount];
        row->type1[0] = '\0';
        row->type2[0] = '\0';

        rest = GetWord(line, row->opcode, sizeof(row->opcode));
        rest = GetWord(rest, row->mnemonic, sizeof(row->mnemonic));
        rest = GetWord(rest, countText, sizeof(countText));

        if (row->mnemonic[0] == '\0' || GetNumber(countText, &count) == 0 ||
            count < 0 || count > 2)
        {
            printf("Warning: %s line %d is not a valid row, skipped\n", fileName, lineNumber);
            continue;
        }

        if (count >= 1) rest = GetWord(rest, row->type1, sizeof(row->type1));
        if (count >= 2) rest = GetWord(rest, row->type2, sizeof(row->type2));
        rest = GetWord(rest, row->modrm, sizeof(row->modrm));
        rest = GetWord(rest, extText, sizeof(extText));

        if ((count >= 1 && row->type1[0] == '\0') ||
            (count >= 2 && row->type2[0] == '\0') ||
            row->modrm[0] == '\0' || GetNumber(extText, &ext) == 0)
        {
            printf("Warning: %s line %d is not a valid row, skipped\n", fileName, lineNumber);
            continue;
        }

        row->operandCount = (int)count;
        row->ext = (int)ext;
        ToLower(row->mnemonic);
        ToLower(row->type1);
        ToLower(row->type2);
        tableCount++;
    }

    fclose(fp);
    return 1;
}

int FindForm(char *mnemonic, int count, char *t1, char *t2)
{
    int i;

    for (i = 0; i < tableCount; i++)
    {
        if (strcmp(table[i].mnemonic, mnemonic) != 0) continue;
        if (table[i].operandCount != count) continue;
        if (count >= 1 && strcmp(table[i].type1, t1) != 0) continue;
        if (count >= 2 && strcmp(table[i].type2, t2) != 0) continue;
        return i;
    }
    return -1;
}

int MnemonicExists(char *mnemonic)
{
    int i;
    for (i = 0; i < tableCount; i++)
        if (strcmp(table[i].mnemonic, mnemonic) == 0)
            return 1;
    return 0;
}

void Step1(char *asmFile)
{
    FILE *fp;
    char line[MAX_LINE], section[SECTION_SIZE] = "";
    char label[NAME_SIZE], mnemonic[NAME_SIZE];
    char ops[MAX_ITEMS][MAX_ITEM];
    char *rest, *operands;
    struct DataLine d;
    int found = 0, notFound = 0;

    printf("\n=========== STEP 1 : OPCODE CHECK ===========\n");

    if (LoadOpcodeTable("instructions.txt") == 0)
    {
        printf("Cannot open instructions.txt\n");
        return;
    }
    printf("Opcode table loaded: %d entries\n\n", tableCount);

    fp = fopen(asmFile, "r");
    if (fp == NULL)
    {
        printf("Cannot open %s\n", asmFile);
        return;
    }
    lineNumber = 0;

    while (ReadLine(fp, line))
    {
        if (line[0] == '\0') continue;
        if (IsSectionLine(line, section)) continue;
        if (IsDirective(line)) continue;

        if (IsLabelLine(line, label, &rest) && *rest == '\0')
            continue;

        if (strcmp(section, ".data") == 0 ||
            strcmp(section, ".bss") == 0) continue;
        if (ParseDataLine(rest, &d) != 0) continue;

        operands = GetWord(rest, mnemonic, sizeof(mnemonic));
        ToLower(mnemonic);

        printf("Mnemonic: %s\n", mnemonic);

        if (MnemonicExists(mnemonic))
        {
            int count = SplitValues(operands, ops);
            char t1[8] = "", t2[8] = "";
            int row;

            printf("Status: Found\n");
            found++;

            if (count < 0) count = 0;
            if (count > 0) snprintf(t1, sizeof(t1), "%s", OperandType(ops[0]));
            if (count > 1) snprintf(t2, sizeof(t2), "%s", OperandType(ops[1]));
            if (strcmp(t1, "sym") == 0) strcpy(t1, "imm");
            if (strcmp(t2, "sym") == 0) strcpy(t2, "imm");

            row = FindForm(mnemonic, count, t1, t2);
            if (row >= 0)
            {
                printf("Opcode: %s (%s", table[row].opcode, mnemonic);
                if (count >= 1) printf(" %s", t1);
                if (count >= 2) printf(" %s", t2);
                printf(")\n");
            }
            else
                printf("Opcode: no table row for these operands\n");
        }
        else
        {
            printf("Status: Not Found\n");
            notFound++;
        }
        printf("\n");
    }

    printf("Summary: %d found, %d not found\n", found, notFound);
    fclose(fp);
}

void Step2(char *asmFile)
{
    FILE *fp;
    char line[MAX_LINE], section[SECTION_SIZE] = "";
    struct DataLine d;
    unsigned char bytes[MAX_BYTES];
    int i, k, n, result;
    long value = 0;

    printf("\n=========== STEP 2 : HEX CONVERSION ===========\n");

    fp = fopen(asmFile, "r");
    if (fp == NULL)
    {
        printf("Cannot open %s\n", asmFile);
        return;
    }
    lineNumber = 0;

    while (ReadLine(fp, line))
    {
        if (line[0] == '\0') continue;
        if (IsSectionLine(line, section)) continue;
        if (strcmp(section, ".text") == 0) continue;

        result = ParseDataLine(line, &d);
        if (result < 0) continue;
        if (result == 0)
        {
            if (!IsDirective(line))
                printf("Warning line %d: not a DB/DD line, ignored\n", lineNumber);
            continue;
        }

        printf("Variable: %s\n", d.name);

        if (strcmp(d.type, "dd") == 0)
        {
            printf("DD Value: ");
            for (i = 0; i < d.itemCount; i++)
            {
                printf("%s", d.items[i]);
                if (i < d.itemCount - 1) printf(", ");
            }
            printf("\n");
        }

        printf("Hexadecimal:");
        for (i = 0; i < d.itemCount; i++)
        {
            n = MakeBytes(d.type, d.items[i], bytes, MAX_BYTES);
            if (n < 0)
            {
                printf(" <bad value '%s'>", d.items[i]);
                continue;
            }

            if (strcmp(d.type, "dd") == 0)
            {

                GetNumber(d.items[i], &value);
                printf(" %02lX", (unsigned long)value & 0xFFFFFFFFUL);
            }
            else
            {
                for (k = 0; k < n; k++)
                    printf(" %02X", bytes[k]);
            }
        }
        printf("\n\n");
    }
    fclose(fp);
}

void Step3(char *asmFile)
{
    FILE *fp;
    char line[MAX_LINE], section[SECTION_SIZE] = "";
    struct DataLine d;
    unsigned char bytes[MAX_BYTES];
    long offset = 0;
    int total, i, result;

    printf("\n=========== STEP 3 : OFFSET + LITTLE-ENDIAN ===========\n");
    printf("OFFSET   HEX_DATA  DECLARATION\n");

    fp = fopen(asmFile, "r");
    if (fp == NULL)
    {
        printf("Cannot open %s\n", asmFile);
        return;
    }
    lineNumber = 0;

    while (ReadLine(fp, line))
    {
        if (line[0] == '\0') continue;

        if (IsSectionLine(line, section))
        {
            if (strcmp(section, ".data") == 0)
                offset = 0;
            continue;
        }
        if (strcmp(section, ".data") != 0) continue;

        result = ParseDataLine(line, &d);
        if (result < 0) continue;
        if (result == 0)
        {
            printf("Warning line %d: not a DB/DD line, ignored\n", lineNumber);
            continue;
        }

        total = MakeAllBytes(&d, bytes);
        if (total < 0) continue;

        printf("%08lX ", offset);
        for (i = 0; i < total; i++)
            printf("%02X", bytes[i]);
        printf(" %s %s ", d.name, d.type);
        PrintItems(&d);
        printf("\n");

        offset = offset + total;
    }
    fclose(fp);
}

int IsGlobalName(char *name)
{
    int i;
    for (i = 0; i < globalCount; i++)
        if (strcmp(globalNames[i], name) == 0)
            return 1;
    return 0;
}

int SymbolExists(char *name)
{
    int i;
    for (i = 0; i < symbolCount; i++)
        if (strcmp(symbols[i].name, name) == 0)
            return 1;
    return 0;
}

void AddSymbol(char *name, int hasOffset, long offset, int size, char type)
{
    struct Symbol *s;

    if (SymbolExists(name))
    {
        printf("Error line %d: symbol '%s' is already defined\n", lineNumber, name);
        return;
    }
    if (symbolCount >= MAX_SYMBOLS)
    {
        printf("Error line %d: symbol table is full (%d)\n", lineNumber, MAX_SYMBOLS);
        return;
    }

    s = &symbols[symbolCount];
    strcpy(s->name, name);
    s->hasOffset = hasOffset;
    s->offset = offset;
    s->size = size;

    if (IsGlobalName(name))
        s->type = (char)toupper((unsigned char)type);
    else
        s->type = type;

    symbolCount++;
}

void PrintSymbols(FILE *out)
{
    int i;

    fprintf(out, "%-12s %-26s %-6s %s\n", "Name", "Offset", "Size", "Type");

    for (i = 0; i < symbolCount; i++)
    {
        fprintf(out, "%-12s ", symbols[i].name);

        if (symbols[i].hasOffset)
            fprintf(out, "%-26.8lX ", symbols[i].offset);
        else
            fprintf(out, "%-26s ", "Implementation-dependent");

        if (symbols[i].size >= 0)
            fprintf(out, "%-6d ", symbols[i].size);
        else
            fprintf(out, "%-6s ", "-");

        fprintf(out, "%c\n", symbols[i].type);
    }
}

void Step4(char *asmFile)
{
    FILE *fp, *out;
    char line[MAX_LINE], section[SECTION_SIZE] = "";
    char names[MAX_LINE], nameList[MAX_ITEMS][MAX_ITEM];
    char label[NAME_SIZE];
    char *rest;
    struct DataLine d;
    unsigned char bytes[MAX_BYTES];
    long offset = 0;
    int total, result, i, k, count;

    printf("\n=========== STEP 4 : SYMBOL TABLE ===========\n");

    symbolCount = 0;
    globalCount = 0;

    fp = fopen(asmFile, "r");
    if (fp == NULL)
    {
        printf("Cannot open %s\n", asmFile);
        return;
    }
    lineNumber = 0;

    while (ReadLine(fp, line))
    {
        if (IsGlobalLine(line, names, sizeof(names)))
        {
            count = SplitValues(names, nameList);
            for (i = 0; i < count; i++)
            {
                if (globalCount < MAX_GLOBALS)
                {

                    for (k = 0; k < NAME_SIZE - 1 && nameList[i][k] != '\0'; k++)
                        globalNames[globalCount][k] = nameList[i][k];
                    globalNames[globalCount][k] = '\0';
                    globalCount++;
                }
                else
                    printf("Warning line %d: too many global names, '%s' ignored\n",
                           lineNumber, nameList[i]);
            }
        }
    }
    rewind(fp);
    lineNumber = 0;

    while (ReadLine(fp, line))
    {
        if (line[0] == '\0') continue;

        if (IsSectionLine(line, section))
        {
            if (strcmp(section, ".data") == 0)
                offset = 0;
            continue;
        }
        if (IsDirective(line)) continue;

        if (strcmp(section, ".data") == 0)
        {
            result = ParseDataLine(line, &d);
            if (result < 0) continue;
            if (result == 0)
            {
                printf("Warning line %d: not a DB/DD line, ignored\n", lineNumber);
                continue;
            }

            total = MakeAllBytes(&d, bytes);
            if (total < 0) continue;

            AddSymbol(d.name, 1, offset, total, 'd');
            offset = offset + total;
        }
        else if (strcmp(section, ".text") == 0)
        {
            if (IsLabelLine(line, label, &rest))
                AddSymbol(label, 0, 0, -1, 't');
        }
    }
    fclose(fp);

    for (i = 0; i < globalCount; i++)
        if (!SymbolExists(globalNames[i]))
            printf("Warning: global '%s' is not defined in this file\n", globalNames[i]);

    PrintSymbols(stdout);

    out = fopen("symbol_table.txt", "w");
    if (out != NULL)
    {
        PrintSymbols(out);
        fclose(out);
        printf("\nSaved to symbol_table.txt\n");
    }
    else
        printf("\nError: cannot create symbol_table.txt\n");
}

int main(int argc, char *argv[])
{
    char asmFile[256] = "demo.asm";
    char input[32];
    long choice;

    if (argc > 2)
    {
        printf("Usage: %s [file.asm]\n", argv[0]);
        return 1;
    }
    if (argc == 2)
        snprintf(asmFile, sizeof(asmFile), "%s", argv[1]);

    printf("IA-32 Assembler  (input file: %s)\n", asmFile);

    do
    {
        printf("\n1. Step 1 - Opcode check\n");
        printf("2. Step 2 - Hex conversion\n");
        printf("3. Step 3 - Offset + Little-Endian\n");
        printf("4. Step 4 - Symbol table\n");
        printf("5. Run all steps\n");
        printf("0. Exit\n");
        printf("Enter choice: ");

        if (fgets(input, sizeof(input), stdin) == NULL)
            break;
        Trim(input);

        if (GetNumber(input, &choice) == 0 || choice < 0 || choice > 5)
        {
            printf("Invalid choice, enter a number from 0 to 5.\n");
            choice = -1;
            continue;
        }

        if (choice == 1 || choice == 5) Step1(asmFile);
        if (choice == 2 || choice == 5) Step2(asmFile);
        if (choice == 3 || choice == 5) Step3(asmFile);
        if (choice == 4 || choice == 5) Step4(asmFile);
    } while (choice != 0);

    return 0;
}