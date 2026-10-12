section .data
    num1 dd 10
    num2 dd 20
    result dd 0
    msg db 'Addition', 10

section .bss
    answer resd 1

section .text
global main

main:
    mov eax, [num1]
    mov ebx, [num2]
    add eax, ebx
    mov [result], eax
    mov [answer], eax

    mov eax, 1
    mov ebx, 0
