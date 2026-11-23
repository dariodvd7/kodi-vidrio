"""Pasa las ventanas internas de Estuary (diálogos, ajustes, menús, listas) al estilo vidrio.

Reemplaza en todos los XML de la skin los fondos de diálogo, las barras de foco y los botones de Estuary por las
texturas de vidrio de media/vidrio/, y ajusta los colores base. Se puede correr varias veces: solo toca lo que todavía
apunta a las texturas de Estuary. No toca las ventanas propias de Vidrio.
Uso: python3 vidrio_global.py ../skin.vidrio
"""
import os
import re
import sys

SKIN = sys.argv[1]
PROPIAS = {'Home.xml', 'DialogVideoInfo.xml', 'VideoOSD.xml', 'Settings.xml', 'Includes_Vidrio.xml', 'Font.xml'}

# textura de Estuary -> (textura de vidrio, borde 9-slice si el XML no trae uno)
CAMBIOS = {
    'dialogs/dialog-bg-nobo.png': ('vidrio/glass_dialog.png', 40),
    'dialogs/dialog-bg.png': ('vidrio/glass_dialog.png', 40),
    'lists/focus.png': ('vidrio/glass_focus.png', 20),
    'buttons/roundbutton-fo.png': ('vidrio/glass_focus.png', 20),
    'buttons/button-fo.png': ('vidrio/glass_focus.png', 20),
    'buttons/dialogbutton-fo.png': ('vidrio/glass_focus.png', 20),
    'buttons/button-nofo.png': ('vidrio/glass_nofo.png', 20),
    'buttons/dialogbutton-nofo.png': ('vidrio/glass_nofo.png', 20),
}
ETIQUETA = re.compile(r'<(texture|texturefocus|texturenofocus|alttexturefocus|alttexturenofocus|texturebg|textureradioonfocus|textureradiooffocus|'
                      r'texturesliderbar|bordertexture|imagepath)(\s[^>]*)?>\s*([^<]+?)\s*</\1>')


def reemplazar(m):
    tag, attrs, ruta = m.group(1), m.group(2) or '', m.group(3)
    if ruta not in CAMBIOS:
        return m.group(0)
    nueva, borde = CAMBIOS[ruta]
    if 'border=' in attrs:
        attrs = re.sub(r'border="[^"]*"', f'border="{borde}"', attrs)
    else:
        attrs = f' border="{borde}"' + attrs
    return f'<{tag}{attrs}>{nueva}</{tag}>'


total = 0
carpeta = os.path.join(SKIN, 'xml')
for nombre in sorted(os.listdir(carpeta)):
    if not nombre.endswith('.xml') or nombre in PROPIAS or nombre.startswith('Custom_115'):
        continue
    ruta = os.path.join(carpeta, nombre)
    texto = open(ruta, encoding='utf-8').read()
    nuevo, n = ETIQUETA.subn(reemplazar, texto)
    cambios = sum(1 for a, b in zip(ETIQUETA.findall(texto), ETIQUETA.findall(nuevo)) if a != b)
    if nuevo != texto:
        open(ruta, 'w', encoding='utf-8').write(nuevo)
        total += cambios
print(f'texturas reemplazadas: {total}')

# Colores base: foco blanco (las texturas de foco ya son traslúcidas), fondos oscuros neutros
colores = os.path.join(SKIN, 'colors', 'defaults.xml')
texto = open(colores, encoding='utf-8').read()
for nombre, valor in {'primary_background': 'FF0A0A0E', 'secondary_background': '33FFFFFF', 'dialog_tint': 'FF1E1E26',
                      'button_focus': 'FFFFFFFF', 'button_alt_focus': '60FFFFFF', 'selected': 'FF9BD0FF',
                      'border_alpha': '40FFFFFF'}.items():
    texto = re.sub(rf'(<color name="{nombre}">)[0-9A-Fa-f]{{8}}(</color>)', rf'\g<1>{valor}\g<2>', texto)
open(colores, 'w', encoding='utf-8').write(texto)
print('colores ajustados')
