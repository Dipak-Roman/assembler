#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void display_expanded_macro(char macro_body[][256], int total_lines,
                            char parameters[][50], int total_parameters)
{
    int line_no, pos, param_no;

    for (line_no = 0; line_no < total_lines; line_no++)
    {
        pos = 0;

        while (macro_body[line_no][pos] != '\0')
        {
            if (macro_body[line_no][pos] == '%' &&
                macro_body[line_no][pos + 1] >= '1' &&
                macro_body[line_no][pos + 1] <= '9')
            {
                param_no = macro_body[line_no][pos + 1] - '1';

                if (param_no < total_parameters)
                {
                    printf("%s", parameters[param_no]);
                }

                pos += 2;
            }
            else
            {
                printf("%c", macro_body[line_no][pos]);
                pos++;
            }
        }
    }
}

int main(int argc, char *argv[])
{
    FILE *input_file;
    char current_line[256];

    char macro_label[50];
    char macro_body[50][256];
    char parameters[10][50];

    int parameter_count = 0;
    int line_count = 0;
    int macro_started = 0;
    int i, j;

    if (argc != 2)
    {
        printf("Usage: ./getmacro input.asm\n");
        return 1;
    }

    input_file = fopen(argv[1], "r");

    if (input_file == NULL)
    {
        printf("File not found\n");
        return 1;
    }

    while (fgets(current_line, sizeof(current_line), input_file) != NULL)
    {
        i = 0;

        if (strncmp(current_line, "%macro", 6) == 0)
        {
            sscanf(current_line, "%%macro %s %d", macro_label, &parameter_count);
            macro_started = 1;
            line_count = 0;
            continue;
        }

        if (strncmp(current_line, "%endmacro", 9) == 0)
        {
            macro_started = 0;
            continue;
        }

        if (macro_started == 1)
        {
            if (line_count < 50)
            {
                strcpy(macro_body[line_count], current_line);
                line_count++;
            }
            continue;
        }

        j = 0;

        while (current_line[i] == ' ' || current_line[i] == '\t')
        {
            i++;
        }

        while (current_line[i] != ' ' && current_line[i] != '\t' &&
               current_line[i] != '\n' && current_line[i] != '\0')
        {
            parameters[0][j] = current_line[i];
            i++;
            j++;
        }

        parameters[0][j] = '\0';

        if (strcmp(parameters[0], macro_label) == 0)
        {
            for (j = 0; j < parameter_count; j++)
            {
                while (current_line[i] == ' ' || current_line[i] == '\t' ||
                       current_line[i] == ',')
                {
                    i++;
                }

                int k = 0;

                while (current_line[i] != ' ' && current_line[i] != '\t' &&
                       current_line[i] != '\n' && current_line[i] != '\0' &&
                       current_line[i] != ',')
                {
                    parameters[j][k] = current_line[i];
                    i++;
                    k++;
                }

                parameters[j][k] = '\0';
            }

            display_expanded_macro(macro_body, line_count,
                                   parameters, parameter_count);
        }
        else
        {
            printf("%s", current_line);
        }
    }

    fclose(input_file);
    return 0;
}
