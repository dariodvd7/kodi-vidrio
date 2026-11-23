"""Genera las texturas de la skin Vidrio (máscaras redondeadas, vidrio y degradados)."""
import os, sys
from PIL import Image, ImageDraw, ImageFilter
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
S = 4  # supersampling para bordes suaves

def rr(w, h, r, fill, outline=None, width=0, name=None):
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], r * S, fill=fill, outline=outline, width=width * S)
    im = im.resize((w, h), Image.LANCZOS)
    im.save(os.path.join(OUT, name))
    return im

# máscara de tarjeta (diffuse): blanco opaco con esquinas redondeadas
rr(400, 225, 22, (255, 255, 255, 255), name='mask_card.png')
rr(300, 450, 20, (255, 255, 255, 255), name='mask_poster.png')
rr(300, 450, 20, (0, 0, 0, 0), (255, 255, 255, 235), 5, name='poster_focus.png')
# borde de foco: aro blanco brillante
rr(400, 225, 22, (0, 0, 0, 0), (255, 255, 255, 235), 4, name='card_focus.png')
rr(120, 120, 30, (0, 0, 0, 0), (255, 255, 255, 235), 4, name='card_focus_panel.png')  # 9-slice, borde 30

def vidrio(w, h, r, alpha, name, borde=70):
    """Panel de vidrio: relleno traslúcido, brillo arriba y filete claro."""
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    base = Image.new('RGBA', im.size, (255, 255, 255, alpha))
    grad = Image.new('L', (1, h * S))
    for y in range(h * S):
        t = y / (h * S)
        grad.putpixel((0, y), int(255 * (1.0 - 0.45 * t)))
    base.putalpha(Image.eval(grad.resize(im.size), lambda v: v * alpha // 255))
    mask = Image.new('L', im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * S - 1, h * S - 1], r * S, fill=255)
    im.paste(base, (0, 0), mask)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([1, 1, w * S - 2, h * S - 2], r * S, outline=(255, 255, 255, borde), width=2 * S)
    im = im.resize((w, h), Image.LANCZOS)
    im.save(os.path.join(OUT, name))

vidrio(120, 80, 40, 46, 'glass_pill.png')            # barra de pestañas (9-slice, borde 40)
vidrio(120, 80, 40, 255, 'pill_focus.png', borde=0)  # pestaña con foco: blanca opaca
vidrio(120, 120, 30, 40, 'glass_panel.png')          # paneles (9-slice, borde 30)
vidrio(120, 120, 30, 70, 'glass_panel_focus.png', borde=120)

def degradado(w, h, curva, name, vertical=True, color=(0, 0, 0)):
    im = Image.new('RGBA', (w, h))
    n = h if vertical else w
    for i in range(n):
        a = int(255 * curva(i / (n - 1)))
        if vertical:
            for x in range(w): im.putpixel((x, i), (*color, a))
        else:
            for y in range(h): im.putpixel((i, y), (*color, a))
    im.save(os.path.join(OUT, name))

suave = lambda t: t * t * (3 - 2 * t)
degradado(4, 512, lambda t: suave(t), 'fade_bottom.png', color=(10, 10, 14))  # transparente arriba -> color del fondo (#0A0A0E)
degradado(512, 4, lambda t: 0.85 * suave(1 - t), 'fade_left.png', False)  # negro a la izquierda
degradado(4, 256, lambda t: 0.7 * suave(1 - t), 'fade_top.png')          # sombra suave arriba (barra)
Image.new('RGBA', (8, 8), (255, 255, 255, 255)).save(os.path.join(OUT, 'white.png'))
# lupa del campo de búsqueda
im = Image.new('RGBA', (64 * S, 64 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
d.ellipse([6 * S, 6 * S, 42 * S, 42 * S], outline=(255, 255, 255, 255), width=6 * S)
d.line([37 * S, 37 * S, 58 * S, 58 * S], fill=(255, 255, 255, 255), width=7 * S)
im.resize((64, 64), Image.LANCZOS).save(os.path.join(OUT, 'lupa.png'))
# Diálogos y focos para todas las ventanas internas (reemplazan las texturas de Estuary)
def panel(w, h, r, relleno, borde, name, brillo=0.0, grosor=2):
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    capa = Image.new('RGBA', im.size, relleno)
    if brillo:  # brillo suave arriba, como el vidrio
        g = Image.new('L', (1, h * S))
        for y in range(h * S):
            g.putpixel((0, y), int(255 * (1.0 - brillo * y / (h * S))))
        capa.putalpha(Image.eval(g.resize(im.size), lambda v: v * relleno[3] // 255))
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * S - 1, h * S - 1], r * S, fill=255)
    im.paste(capa, (0, 0), m)
    if borde:
        ImageDraw.Draw(im).rounded_rectangle([1, 1, w * S - 2, h * S - 2], r * S, outline=borde, width=grosor * S)
    im.resize((w, h), Image.LANCZOS).save(os.path.join(OUT, name))

panel(160, 160, 36, (30, 30, 38, 240), (255, 255, 255, 46), 'glass_dialog.png', brillo=0.25)  # 9-slice, borde 40
panel(120, 120, 20, (255, 255, 255, 64), (255, 255, 255, 210), 'glass_focus.png')            # 9-slice, borde 20
panel(120, 120, 20, (255, 255, 255, 22), (255, 255, 255, 46), 'glass_nofo.png')              # 9-slice, borde 20
print('ok', sorted(os.listdir(OUT)))
