
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

struct Symbol
{
    char name[30];
    char address[20];
    char section[20];
    char size[20];
    char value[50];
};

int main()
{
    FILE *fp;
    char filename[100];
    char line[200];
    char section[20] = "Unknown";

    struct Symbol table[100];
    int count = 0;
    int dataLC = 0, bssLC = 0;

    printf("Enter ASM file name: ");
    scanf("%99s", filename);

    fp = fopen(filename, "r");

    if (fp == NULL)
    {
        printf("File not found!\n");
        return 1;
    }

    while (fgets(line, sizeof(line), fp))
    {
        char name[30], directive[20], value[50];
        int bytes = 0;
        char *p;

        line[strcspn(line, "\n")] = '\0';

        if (line[0] == '\0' || line[0] == ';')
            continue;

        if (strstr(line, "section .data"))
        {
            strcpy(section, ".data");
            continue;
        }

        if (strstr(line, "section .bss"))
        {
            strcpy(section, ".bss");
            continue;
        }

        if (strstr(line, "section .text"))
        {
            strcpy(section, ".text");
            continue;
        }

        p = strchr(line, ';');
        if (p != NULL)
            *p = '\0';

        if (sscanf(line, "%29s %19s %49s",
                   name, directive, value) == 3)
        {
            if (strcmp(directive, "db") == 0)
                bytes = 1;
            else if (strcmp(directive, "dw") == 0)
                bytes = 2;
            else if (strcmp(directive, "dd") == 0)
                bytes = 4;
            else if (strcmp(directive, "dq") == 0)
                bytes = 8;
            else if (strcmp(directive, "resb") == 0)
                bytes = 1;
            else if (strcmp(directive, "resw") == 0)
                bytes = 2;
            else if (strcmp(directive, "resd") == 0)
                bytes = 4;
            else if (strcmp(directive, "resq") == 0)
                bytes = 8;

            if (bytes > 0)
            {
                strcpy(table[count].name, name);
                strcpy(table[count].section, section);
                strcpy(table[count].value, value);

                if (strcmp(section, ".data") == 0)
                {
                    sprintf(table[count].address, "%d", dataLC);
                    dataLC += bytes;
                }
                else if (strcmp(section, ".bss") == 0)
                {
                    sprintf(table[count].address, "%d", bssLC);
                    bssLC += bytes;
                }
                else
                {
                    strcpy(table[count].address, "Unknown");
                }

                sprintf(table[count].size, "%d byte(s)", bytes);
                count++;
            }
        }
        else
        {
            char label[30];

            if (sscanf(line, "%29[^:]:", label) == 1)
            {
                if (strchr(line, ':') != NULL)
                {
                    strcpy(table[count].name, label);
                    strcpy(table[count].section, section);
                    strcpy(table[count].size, "-");
                    strcpy(table[count].value, "-");
                    strcpy(table[count].address, "Unknown");
                    count++;
                }
            }
        }
    }

    fclose(fp);

    printf("\n----------- SYMBOL TABLE -----------\n");
    printf("%-15s %-15s %-10s %-12s %-15s\n",
           "Symbol Name", "Symbol Address",
           "Section", "Size", "Value");

    printf("---------------------------------------------------------------\n");

    for (int i = 0; i < count; i++)
    {
        printf("%-15s %-15s %-10s %-12s %-15s\n",
               table[i].name,
               table[i].address,
               table[i].section,
               table[i].size,
               table[i].value);
    }

    return 0;
}

/*jamdh@Anvi:~/System2$ ./myexe
Enter ASM file name: test2.asm

----------- SYMBOL TABLE -----------
Symbol Name     Symbol Address  Section    Size         Value
---------------------------------------------------------------
NUM             0               .data      1 byte(s)    10
VAL             1               .data      2 byte(s)    20
ARR             3               .data      4 byte(s)    100
COUNT           0               .bss       4 byte(s)    1
START           Unknown         .text      -            -
LOOP            Unknown         .text      -            -
jamdh@Anvi:~/System2$*/