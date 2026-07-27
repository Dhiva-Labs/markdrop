"""Stub for cryptography (real wheel's _rust.so is 4KB-aligned and cannot load
on 16KB page-size Android). pdfminer imports two symbols and only calls them
for ENCRYPTED PDFs — normal PDFs never touch this. Encrypted PDFs raise a
clear error instead."""
