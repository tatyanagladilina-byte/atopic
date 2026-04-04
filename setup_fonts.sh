#!/bin/bash
# Download Cormorant Garamond fonts for Atopic brand style
mkdir -p /app/fonts

echo "Downloading Cormorant Garamond fonts..."

# Download from Google Fonts GitHub
BASE="https://github.com/CatharsisFonts/Cormorant/raw/master/fonts/ttf"

wget -q "$BASE/Cormorant-Regular.ttf"    -O /app/fonts/Cormorant-Regular.ttf    && echo "Regular OK"
wget -q "$BASE/Cormorant-Italic.ttf"     -O /app/fonts/Cormorant-Italic.ttf     && echo "Italic OK"
wget -q "$BASE/Cormorant-SemiBold.ttf"   -O /app/fonts/Cormorant-SemiBold.ttf   && echo "SemiBold OK"
wget -q "$BASE/Cormorant-Light.ttf"      -O /app/fonts/Cormorant-Light.ttf      && echo "Light OK"

echo "Font setup complete."
