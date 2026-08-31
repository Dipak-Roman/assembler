#include <stdio.h>
#include <string.h>
#include <ctype.h>

#define MAX 100

char *instructions[MAX] = 
{
    "MOV", "PUSH", "POP", "XCHG", "LEA",

    "ADD", "SUB", "INC", "DEC",
    "MUL", "IMUL", "DIV", "IDIV", "NEG",

    "AND", "OR", "XOR", "NOT",

    "SHL", "SHR", "SAL", "SAR",

    "ROL", "ROR", "RCL", "RCR",

    "CMP", "TEST",

    "JMP", "JE", "JZ", "JNE", "JNZ",
    "JG", "JGE", "JL", "JLE",
    "JA", "JAE", "JB", "JBE",

    "CALL", "RET", "LOOP",

    "INT", "IRET",

    "CLC", "STC", "CMC",
    "CLD", "STD",
    "CLI", "STI",

    "IN", "OUT",

    "NOP", "HLT", "WAIT", "CPUID"
};

void uppercase(char str[])
{
    int i;

    for (i = 0; str[i] != '\0'; i++)
    {
        str[i] = toupper(str[i]);
    }
}
int checkInstruction(char word[])
{
    int i;

    for (i = 0; instructions[i] != NULL; i++)
    {
        if (strcmp(word, instructions[i]) == 0)
        {
            return 1;
        }
    }

    return 0;
}

int main(int argc, char *argv[])
{
    FILE *file;
    FILE *log;

    char line[200];
    char instruction[50];

    int lineNumber = 0;

    if (argc != 2)
    {
        printf("Usage: %s <file.asm>\n", argv[0]);
        return 1;
    }
    file = fopen(argv[1], "r");

    if (file == NULL)
    {
        printf("Error: Cannot open file.\n");
        return 1;
    }

    log = fopen("instruction.log", "w");

    if (log == NULL)
    {
        printf("Error: Cannot create log file.\n");
        fclose(file);
        return 1;
    }
    while (fgets(line, sizeof(line), file) != NULL)
    {
        lineNumber++;

        if (sscanf(line, "%s", instruction) != 1)
        {
            continue;
        }
        if (instruction[strlen(instruction) - 1] == ':')
        {
            continue;
        }
        uppercase(instruction);

        if (checkInstruction(instruction))
        {
            printf("Line %d : %s -> VALID\n",
                   lineNumber, instruction);

            fprintf(log, "Line %d : %s -> VALID\n",
                    lineNumber, instruction);
        }
        else
        {
            printf("Line %d : %s -> INVALID\n",
                   lineNumber, instruction);

            fprintf(log, "Line %d : %s -> INVALID\n",
                    lineNumber, instruction);
        }
    }

    fclose(file);
    fclose(log);

    printf("\nLog file created: instruction.log\n");

    return 0;
}
//=====================================================================================
//output
//=====================================================================================
/*jamdh@Anvi:~/System2$ gcc Instruction.c -o myexe
jamdh@Anvi:~/System2$ ./myexe
Usage: ./myexe <file.asm>
jamdh@Anvi:~/System2$ ./myexe program.asm
Line 2 : MOV -> VALID
Line 3 : ADD -> VALID
Line 4 : SUB -> VALID
Line 5 : INC -> VALID
Line 6 : DEC -> VALID
Line 8 : PUSH -> VALID
Line 9 : POP -> VALID
Line 11 : CMP -> VALID
Line 12 : JMP -> VALID
Line 15 : XOR -> VALID
Line 16 : NOP -> VALID
Line 18 : ABC -> INVALID
Line 19 : HELLO -> INVALID
Line 20 : XYZ -> INVALID

Log file created: instruction.log*/