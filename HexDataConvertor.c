
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

void RemoveSpaces(char *str)
{
    int iStart = 0;
    int iEnd = strlen(str) - 1;

    while (isspace((unsigned char)str[iStart]))
    {
        iStart++;
    }

    while (iEnd >= iStart && isspace((unsigned char)str[iEnd]))
    {
        str[iEnd] = '\0';
        iEnd--;
    }

    if (iStart > 0)
    {
        memmove(str, str + iStart, strlen(str + iStart) + 1);
    }
}

void PrintHex(char *str)
{
    int iCount = 0;

    while (str[iCount] != '\0')
    {
        printf("%02X ", (unsigned char)str[iCount]);
        iCount++;
    }
}

void ConvertDB(char *value)
{
    char szText[800];
    char *ptr;
    char *end;
    long iNumber;

    strcpy(szText, value);
    RemoveSpaces(szText);

    int iLength = strlen(szText);

    /* Handle quoted strings */
    if (iLength >= 2 &&
        ((szText[0] == '\'' && szText[iLength - 1] == '\'') ||
         (szText[0] == '"' && szText[iLength - 1] == '"')))
    {
        szText[iLength - 1] = '\0';

        printf("ASCII     : %s\n", szText + 1);
        printf("Hex       : ");
        PrintHex(szText + 1);
        printf("\n");
    }
    else
    {
        char szCopy[800];
        char szAscii[800] = "";
        char *szPart;

        strcpy(szCopy, szText);

        szPart = strtok(szCopy, ",");

        while (szPart != NULL)
        {
            RemoveSpaces(szPart);

            iNumber = strtol(szPart, &end, 0);

            if (end != szPart && *end == '\0' &&
                iNumber >= 0 && iNumber <= 255)
            {
                int iAsciiLength = strlen(szAscii);

                szAscii[iAsciiLength] = (char)iNumber;
                szAscii[iAsciiLength + 1] = '\0';

                printf("%02lX ", iNumber);
            }
            else
            {
                strcat(szAscii, szPart);
                PrintHex(szPart);
            }

            szPart = strtok(NULL, ",");
        }

        printf("\nASCII     : %s\n", szAscii);
    }
}

void ConvertDD(char *value)
{
    char *end;
    long iNumber;

    RemoveSpaces(value);

    iNumber = strtol(value, &end, 0);

    if (end != value && *end == '\0')
    {
        printf("Hex       : %08X\n", (unsigned int)iNumber);
    }
    else
    {
        printf("Hex       : Invalid value\n");
    }
}

void InspectDataSection(char *szFileName)
{
    FILE *fp;
    char szLine[1024];
    char szStatement[1024];
    char szVariable[100];
    char szType[20];
    char szValue[800];

    int iLineNumber = 0;
    int iDataSection = 0;

    fp = fopen(szFileName, "r");

    if (fp == NULL)
    {
        printf("Error: Unable to open file %s\n", szFileName);
    }
    else
    {
        while (fgets(szLine, sizeof(szLine), fp) != NULL)
        {
            iLineNumber++;

            /* Remove comments */
            char *ptr = strchr(szLine, ';');

            if (ptr != NULL)
            {
                *ptr = '\0';
            }

            RemoveSpaces(szLine);

            if (strlen(szLine) == 0)
            {
                continue;
            }

            /* Check data section */
            if (strcmp(szLine, ".data") == 0 ||
                strcmp(szLine, "section .data") == 0 ||
                strcmp(szLine, "SECTION .DATA") == 0)
            {
                iDataSection = 1;

                printf("\n====================================================\n");
                printf("DATA SECTION\n");
                printf("====================================================\n");

                continue;
            }

            if (strncmp(szLine, "section ", 8) == 0 ||
                strncmp(szLine, "SECTION ", 8) == 0)
            {
                iDataSection = 0;
                continue;
            }

            if (iDataSection == 0)
            {
                continue;
            }

            /* Read variable name, data type and value */
            strcpy(szStatement, szLine);

            if (sscanf(szStatement, "%99s %19s %799[^\n]",
                       szVariable, szType, szValue) != 3)
            {
                continue;
            }

            /* Convert data type to uppercase */
            int iCount = 0;

            while (szType[iCount] != '\0')
            {
                szType[iCount] = toupper((unsigned char)szType[iCount]);
                iCount++;
            }

            if (strcmp(szType, "DB") != 0 &&
                strcmp(szType, "DD") != 0)
            {
                continue;
            }

            RemoveSpaces(szValue);

            printf("\n----------------------------------------------------\n");
            printf("Line      : %d\n", iLineNumber);
            printf("Statement : %s\n", szLine);
            printf("Variable  : %s\n", szVariable);
            printf("Type      : %s\n", szType);
            printf("Value     : %s\n", szValue);

            if (strcmp(szType, "DB") == 0)
            {
                ConvertDB(szValue);
            }
            else
            {
                ConvertDD(szValue);
            }
        }

        fclose(fp);
    }
}

int main(int argc, char *argv[])
{
    char szFileName[256];

    printf("ASM Data Converter\n");
    printf("====================================================\n");

    if (argc == 2)
    {
        strcpy(szFileName, argv[1]);
    }
    else
    {
        printf("Enter assembly file name: ");
        scanf("%255s", szFileName);
    }

    InspectDataSection(szFileName);

    printf("\n====================================================\n");
    printf("Conversion completed.\n");

    return 0;
}
/*output->
jamdh@Anvi:~/System2$ gcc HexDataConvertor.c -o myexe
jamdh@Anvi:~/System2$ ./myexe
ASM Data Converter
====================================================
Enter assembly file name: sample.asm

====================================================
DATA SECTION
====================================================

----------------------------------------------------
Line      : 3
Statement : msg     DB 'HELLO'
Variable  : msg
Type      : DB
Value     : 'HELLO'
ASCII     : HELLO
Hex       : 48 45 4C 4C 4F

----------------------------------------------------
Line      : 4
Statement : letter  DB 'A'
Variable  : letter
Type      : DB
Value     : 'A'
ASCII     : A
Hex       : 41

----------------------------------------------------
Line      : 5
Statement : values  DB 65,66,67
Variable  : values
Type      : DB
Value     : 65,66,67
41 42 43
ASCII     : ABC

----------------------------------------------------
Line      : 6
Statement : number  DD 100
Variable  : number
Type      : DD
Value     : 100
Hex       : 00000064

----------------------------------------------------
Line      : 7
Statement : hexnum  DD 0xFF
Variable  : hexnum
Type      : DD
Value     : 0xFF
Hex       : 000000FF

----------------------------------------------------
Line      : 8
Statement : digit   DB 48
Variable  : digit
Type      : DB
Value     : 48
30
ASCII     : 0

----------------------------------------------------
Line      : 9
Statement : text    DB "Hello World"
Variable  : text
Type      : DB
Value     : "Hello World"
ASCII     : Hello World
Hex       : 48 65 6C 6C 6F 20 57 6F 72 6C 64

----------------------------------------------------
Line      : 10
Statement : newline DB 10
Variable  : newline
Type      : DB
Value     : 10
0A
ASCII     :


====================================================
Conversion completed.
*/