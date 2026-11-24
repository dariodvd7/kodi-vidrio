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


def favoritos():
    """Equipos favoritos de la casa ("favoritos" en local.json, como en el ajuste: "Racing Club, Packers"), o ''."""
    try:
        with open(ARCHIVO, encoding='utf-8') as fh:
            return json.load(fh).get('favoritos') or ''
    except FileNotFoundError:
        return ''


def aplicar(carpeta_plugin, ip=None):
    """Pone la IP del homelab en el valor por defecto del catálogo del plugin ya copiado y, salvo en el paquete
    genérico (IP de ejemplo), los equipos favoritos de la casa en el valor por defecto de "Equipos favoritos"."""
    import re
    ip = ip or homelab()
    ruta = os.path.join(carpeta_plugin, 'resources', 'settings.xml')
    with open(ruta, encoding='utf-8') as fh:
        xml = fh.read()
    xml = xml.replace(f'smb://{EJEMPLO}/', f'smb://{ip}/')
    if ip != EJEMPLO and favoritos():
        xml = re.sub(r'(<setting id="equipos_favoritos"[^>]*>\s*<level>\d</level>\s*<default>)(</default>)',
                     lambda m: m.group(1) + favoritos().replace('&', '&amp;') + m.group(2), xml, count=1)
    with open(ruta, 'w', encoding='utf-8') as fh:
        fh.write(xml)
    return ip


def aplicar_repositorio(carpeta_repo, ip=None):
    """Pone la IP del homelab en las direcciones del repositorio (repository.vidrio) ya copiado."""
    ip = ip or homelab()
    ruta = os.path.join(carpeta_repo, 'addon.xml')
    with open(ruta, encoding='utf-8') as fh:
        xml = fh.read()
    with open(ruta, 'w', encoding='utf-8') as fh:
        fh.write(xml.replace(f'http://{EJEMPLO}:', f'http://{ip}:'))
    return ip
