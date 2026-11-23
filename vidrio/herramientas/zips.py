#!/usr/bin/env python3
"""Arma dist/plugin.video.vidrio-<versión>.zip y dist/skin.vidrio-<versión>.zip para instalar desde un zip.

El plugin sale con la IP real del homelab de local.json (o la de ejemplo con --generico).
Uso: python3 herramientas/zips.py [--generico]
"""
import os
import re
import shutil
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import local  # noqa: E402

VIDRIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IGNORAR = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store')


def version(carpeta):
    xml = open(os.path.join(VIDRIO, carpeta, 'addon.xml'), encoding='utf-8').read()
    return re.search(r'<addon[^>]*\sversion="([^"]+)"', xml).group(1)


def main():
    generico = '--generico' in sys.argv
    with tempfile.TemporaryDirectory() as tmp:
        for carpeta in ('plugin.video.vidrio', 'skin.vidrio'):
            copia = os.path.join(tmp, carpeta)
            shutil.copytree(os.path.join(VIDRIO, carpeta), copia, ignore=IGNORAR)
            if carpeta == 'plugin.video.vidrio':
                print('homelab:', local.aplicar(copia, local.EJEMPLO if generico else None))
            salida = os.path.join(VIDRIO, 'dist', f'{carpeta}-{version(carpeta)}.zip')
            with zipfile.ZipFile(salida, 'w', zipfile.ZIP_DEFLATED) as z:
                for raiz, dirs, archivos in os.walk(copia):
                    dirs.sort()
                    for nombre in sorted(archivos):
                        ruta = os.path.join(raiz, nombre)
                        z.write(ruta, os.path.relpath(ruta, tmp))
            print(salida)


if __name__ == '__main__':
    main()
