
#include<stdio.h>
#include<string.h>
#include<stdlib.h>

void expand_macro(char body[][256], int count,
                  char args[][50], int arg_count)
{
    int i, j, index;

    for(i = 0; i < count; i++)
    {
        j = 0;

        while(body[i][j] != '\0')
        {
            if(body[i][j] == '%' &&
               body[i][j+1] >= '1' &&
               body[i][j+1] <= '9')
            {
                index = body[i][j+1] - '1';

                if(index < arg_count)
                {
                    printf("%s", args[index]);
                }

                j = j + 2;
            }
            else
            {
                printf("%c", body[i][j]);
                j++;
            }
        }
    }
}

int main(int argc, char *argv[])
{
    FILE *fp;
    char line[256];

    char macro_name[50];
    char body[50][256];
    char args[10][50];

    int arg_count = 0;
    int body_count = 0;
    int inside_macro = 0;

    int i, j;

    if(argc != 2)
    {
        printf("Usage: ./getmacro input.asm\n");
        return 1;
    }

    fp = fopen(argv[1], "r");

    if(fp == NULL)
    {
        printf("File not found\n");
        return 1;
    }

    while(fgets(line, sizeof(line), fp) != NULL)
    {
        i = 0;

        if(strncmp(line, "%macro", 6) == 0)
        {
            sscanf(line, "%%macro %s %d",
                   macro_name, &arg_count);

            inside_macro = 1;
            body_count = 0;

            continue;
        }

        if(strncmp(line, "%endmacro", 9) == 0)
        {
            inside_macro = 0;
            continue;
        }

        if(inside_macro == 1)
        {
            if(body_count < 50)
            {
                strcpy(body[body_count], line);
                body_count++;
            }

            continue;
        }

        j = 0;

        while(line[i] == ' ' || line[i] == '\t')
        {
            i++;
        }

        while(line[i] != ' ' && line[i] != '\t' &&
              line[i] != '\n' && line[i] != '\0')
        {
            args[0][j] = line[i];
            i++;
            j++;
        }

        args[0][j] = '\0';

        if(strcmp(args[0], macro_name) == 0)
        {
            for(j = 0; j < arg_count; j++)
            {
                while(line[i] == ' ' || line[i] == '\t' ||
                      line[i] == ',')
                {
                    i++;
                }

                int k = 0;

                while(line[i] != ' ' && line[i] != '\t' &&
                      line[i] != '\n' && line[i] != '\0' &&
                      line[i] != ',')
                {
                    args[j][k] = line[i];
                    i++;
                    k++;
                }

                args[j][k] = '\0';
            }

            expand_macro(body, body_count, args, arg_count);
        }
        else
        {
            printf("%s", line);
        }
    }

    fclose(fp);

    return 0;
}
/*
OUTPUT-->
jamdh@Anvi:~/System2$ ./myexe
Usage: ./getmacro input.asm
jamdh@Anvi:~/System2$ ./getmacro input.asm

START:
MOV AX, 5
MOV BX, 4
MUL BX
MOV CX, AXjamdh@Anvi:~/System2$
*/