#include <stdio.h>
#include <string.h>
#include <ctype.h>

char *registers[] = 
{
    "AX", "BX", "CX", "DX",
    "SI", "DI", "SP", "BP",
    "AL", "AH", "BL", "BH",
    "CL", "CH", "DL", "DH",
    NULL
};

int isRegister(char *op)
{
    int i;

    for (i = 0; registers[i] != NULL; i++)
    {
        if (strcmp(op, registers[i]) == 0)
            return 1;
    }

    return 0;
}
int isConstant(char *op)
{
    int i;

    for (i = 0; op[i] != '\0'; i++)
    {
        if (!isdigit(op[i]))
            return 0;
    }

    return 1;
}

int main(int argc, char *argv[])
{
    FILE *file;
    char line[200];
    char instruction[20];
    char *operand;
    char *comment;

    if (argc != 2)
    {
        printf("Usage: %s file.asm\n", argv[0]);
        return 1;
    }

    file = fopen(argv[1], "r");

    if (file == NULL)
    {
        printf("Cannot open file\n");
        return 1;
    }

    while (fgets(line, sizeof(line), file))
    {
        comment = strchr(line, ';');

        if (comment != NULL)
            *comment = '\0';
        if (sscanf(line, "%s", instruction) != 1)
            continue;
        if (instruction[strlen(instruction) - 1] == ':')
            continue;

        printf("\nInstruction: %s\n", instruction);

        operand = strchr(line, ' ');

        if (operand == NULL)
            continue;

        operand++;

        operand = strtok(operand, ",");

        while (operand != NULL)
        {
            while (isspace(*operand))
                operand++;

            operand[strcspn(operand, "\n")] = '\0';

            if (isRegister(operand))
                printf("Operand: %s -> REGISTER\n", operand);

            else if (operand[0] == '[')
                printf("Operand: %s -> MEMORY\n", operand);

            else if (isConstant(operand))
                printf("Operand: %s -> CONSTANT\n", operand);

            else
                printf("Operand: %s -> SYMBOL\n", operand);

            operand = strtok(NULL, ",");
        }
    }

    fclose(file);

    return 0;
}
//===========================================================================
//output
//==========================================================================
/*jamdh@Anvi:~/System2$ gcc operand.c -o myexe
jamdh@Anvi:~/System2$ ./myexe
Usage: ./myexe file.asm
jamdh@Anvi:~/System2$ ./myexe program.asm

Instruction: MOV
Operand: AX -> REGISTER
Operand: BX -> REGISTER

Instruction: ADD
Operand: AX -> REGISTER
Operand: 10 -> CONSTANT

Instruction: SUB
Operand: AX -> REGISTER
Operand: BX -> REGISTER

Instruction: INC
Operand: AX -> REGISTER

Instruction: DEC
Operand: BX -> REGISTER

Instruction: PUSH
Operand: AX -> REGISTER

Instruction: POP
Operand: BX -> REGISTER

Instruction: CMP
Operand: AX -> REGISTER
Operand: BX -> REGISTER

Instruction: JMP
Operand: start -> SYMBOL

Instruction: XOR
Operand: XOR AX -> SYMBOL
Operand: AX -> REGISTER

Instruction: NOP
Operand: NOP -> SYMBOL

Instruction: ABC
Operand: AX -> REGISTER
Operand: BX -> REGISTER

Instruction: HELLO

Instruction: XYZ*/