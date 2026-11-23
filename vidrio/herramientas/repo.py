#!/usr/bin/env python3
"""Arma el repositorio de add-ons de Vidrio (repository.vidrio) y lo sube al homelab.

Kodi lee el repositorio por HTTP: addons.xml (todos los addon.xml juntos), addons.xml.md5 y un zip por add-on en
<id>/<id>-<versión>.zip. En el homelab lo sirve un nginx de solo lectura (puerto 8099, ver homelab/kodi-repo/) desde
/srv/kodi-addons/repo. Con el repositorio instalado y Kodi en "Instalar actualizaciones automáticamente", cada
versión nueva de la skin o el plugin llega sola a todos los Kodi de casa.

Uso:
  python3 herramientas/repo.py            arma dist/repo/ con la IP real (vidrio/local.json)
  python3 herramientas/repo.py --subir    además lo copia al homelab (ssh multimedia)
  python3 herramientas/repo.py --generico arma dist/repo-generico/ con la IP de ejemplo (para publicar)

Para publicar una versión: subir el número en el addon.xml de la skin o el plugin y correr con --subir.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import local  # noqa: E402

VIDRIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDONS = ['plugin.video.vidrio', 'skin.vidrio', 'repository.vidrio']
IGNORAR = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store')
HOMELAB = 'multimedia'
DESTINO = '/srv/kodi-addons/repo'


def version(xml):
    return re.search(r'<addon[^>]*\sversion="([^"]+)"', xml).group(1)


def empaquetar(addon, tmp, salida, ip):
    copia = os.path.join(tmp, addon)
    shutil.copytree(os.path.join(VIDRIO, addon), copia, ignore=IGNORAR)
    if addon == 'plugin.video.vidrio':
        local.aplicar(copia, ip)
    elif addon == 'repository.vidrio':
        local.aplicar_repositorio(copia, ip)
    xml = open(os.path.join(copia, 'addon.xml'), encoding='utf-8').read()
    ver = version(xml)
    os.makedirs(os.path.join(salida, addon), exist_ok=True)
    zip_ruta = os.path.join(salida, addon, f'{addon}-{ver}.zip')
    with zipfile.ZipFile(zip_ruta, 'w', zipfile.ZIP_DEFLATED) as z:
        for raiz, dirs, archivos in os.walk(copia):
            dirs.sort()
            for nombre in sorted(archivos):
                ruta = os.path.join(raiz, nombre)
                z.write(ruta, os.path.relpath(ruta, tmp))
    # Kodi muestra el ícono del repositorio antes de bajar el zip
    for icono in ('icon.png', 'resources/icon.png'):
        if os.path.isfile(os.path.join(copia, icono)):
            shutil.copy(os.path.join(copia, icono), os.path.join(salida, addon, 'icon.png'))
            break
    return re.sub(r'^<\?xml[^>]*\?>\s*', '', xml.strip()), ver


def main():
    generico = '--generico' in sys.argv
    ip = local.EJEMPLO if generico else local.homelab()
    salida = os.path.join(VIDRIO, 'dist', 'repo-generico' if generico else 'repo')
    shutil.rmtree(salida, ignore_errors=True)
    os.makedirs(salida)
    partes = []
    with tempfile.TemporaryDirectory() as tmp:
        for addon in ADDONS:
            xml, ver = empaquetar(addon, tmp, salida, ip)
            partes.append(xml)
            print(f'{addon} {ver}')
    indice = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n' + '\n'.join(partes) + '\n</addons>\n'
    with open(os.path.join(salida, 'addons.xml'), 'w', encoding='utf-8') as fh:
        fh.write(indice)
    with open(os.path.join(salida, 'addons.xml.md5'), 'w', encoding='utf-8') as fh:
        fh.write(hashlib.md5(indice.encode('utf-8')).hexdigest())
    print(f'repositorio: {salida} (homelab {ip})')

    if '--subir' in sys.argv and not generico:
        # Se copia a una carpeta nueva y se cambia de lugar al final: Kodi nunca ve un repositorio a medias.
        subprocess.run(['ssh', HOMELAB, 'rm -rf /tmp/vidrio-repo && mkdir -p /tmp/vidrio-repo'], check=True)
        subprocess.run(['scp', '-q', '-r', salida + '/.', f'{HOMELAB}:/tmp/vidrio-repo/'], check=True)
        subprocess.run(['ssh', HOMELAB,
                        f'sudo rm -rf {DESTINO}.nuevo && sudo cp -r /tmp/vidrio-repo {DESTINO}.nuevo && '
                        f'sudo chmod -R a+rX {DESTINO}.nuevo && sudo rm -rf {DESTINO}.viejo && '
                        f'{{ [ -d {DESTINO} ] && sudo mv {DESTINO} {DESTINO}.viejo || true; }} && '
                        f'sudo mv {DESTINO}.nuevo {DESTINO} && sudo rm -rf {DESTINO}.viejo /tmp/vidrio-repo'],
                       check=True)
        print(f'subido a {HOMELAB}:{DESTINO}')


if __name__ == '__main__':
    main()
