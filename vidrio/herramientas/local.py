"""Datos de la red de casa que no van al repositorio.

vidrio/local.json (ignorado por git; ver local.ejemplo.json) tiene la IP real del homelab. En el código queda la de
ejemplo (192.168.1.50); al empaquetar el plugin (zips.py, fork/armar_ipa.py) se reemplaza por la real.
"""
import json
import os

EJEMPLO = '192.168.1.50'
ARCHIVO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'local.json')


def homelab():
    """IP real del homelab, o la de ejemplo si no hay local.json."""
    try:
        with open(ARCHIVO, encoding='utf-8') as fh:
            return json.load(fh).get('homelab') or EJEMPLO
    except FileNotFoundError:
        return EJEMPLO


def aplicar(carpeta_plugin, ip=None):
    """Pone la IP del homelab en el valor por defecto del catálogo del plugin ya copiado."""
    ip = ip or homelab()
    ruta = os.path.join(carpeta_plugin, 'resources', 'settings.xml')
    with open(ruta, encoding='utf-8') as fh:
        xml = fh.read()
    with open(ruta, 'w', encoding='utf-8') as fh:
        fh.write(xml.replace(f'smb://{EJEMPLO}/', f'smb://{ip}/'))
    return ip
