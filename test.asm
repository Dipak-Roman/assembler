section .data

msg db 'Hello'
name db 'Himani'
num db 25
letter db 'A'
newline db 10

value dd 1000
number dd 255
large_num dd 50000

section .text
global main

main:
    mov eax, 1
    mov ebx, 0
