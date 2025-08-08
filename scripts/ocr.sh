#!/usr/bin/env bash

# Dependencies check
command -v hyprshot >/dev/null 2>&1 || { notify-send -a "Ax-Shell" "OCR Failed" "hyprshot not found"; exit 1; }
command -v tesseract >/dev/null 2>&1 || { notify-send -a "Ax-Shell" "OCR Failed" "tesseract not found"; exit 1; }
command -v wl-copy >/dev/null 2>&1 || { notify-send -a "Ax-Shell" "OCR Failed" "wl-copy not found"; exit 1; }

# Create temp file
tmpfile=$(mktemp --suffix=.png)

# Take screenshot as PNG
hyprshot -m region -z -s -o "$(dirname "$tmpfile")" -f "$(basename "$tmpfile")"

# Check if screenshot was created and is a valid PNG
if [[ ! -f "$tmpfile" ]] || ! file "$tmpfile" | grep -q "PNG image data"; then
    rm -f "$tmpfile"
    notify-send -a "Ax-Shell" "OCR Failed" "Screenshot failed"
    exit 1
fi

# Run tesseract on the PNG
ocr_text=$(tesseract -l eng "$tmpfile" - 2>/dev/null)
rm -f "$tmpfile"

# Trim whitespace
ocr_text=$(echo "$ocr_text" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

# Check if Tesseract returned anything meaningful
if [[ -n "$ocr_text" ]]; then
    echo -n "$ocr_text" | wl-copy
    notify-send -a "Ax-Shell" "OCR Success" "Text Copied to Clipboard"
else
    notify-send -a "Ax-Shell" "OCR Failed" "No text recognized"
fi
