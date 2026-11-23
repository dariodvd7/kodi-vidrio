# -*- coding: utf-8 -*-
"""Lee el catálogo del homelab y lo guarda en caché local."""
import json
import os
import time

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon('plugin.video.vidrio')
PERFIL = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
CACHE = os.path.join(PERFIL, 'catalogo.json')
VIGENCIA = 30 * 60  # segundos antes de volver a leer el catálogo del homelab


def log(msg, nivel=xbmc.LOGINFO):
    xbmc.log(f'[vidrio] {msg}', nivel)


def _leer_remoto():
    ruta = ADDON.getSettingString('catalogo')
    with xbmcvfs.File(ruta) as fh:
        datos = fh.readBytes()
    if not datos:
        raise IOError(f'catálogo vacío o inaccesible: {ruta}')
    return json.loads(bytes(datos).decode('utf-8'))


def cargar(forzar=False):
    """Devuelve el catálogo: caché si está fresca, si no el del homelab; si el homelab falla, la caché vieja."""
    fresco = os.path.isfile(CACHE) and time.time() - os.path.getmtime(CACHE) < VIGENCIA
    if fresco and not forzar:
        with open(CACHE, encoding='utf-8') as fh:
            return json.load(fh)
    try:
        cat = _leer_remoto()
        os.makedirs(PERFIL, exist_ok=True)
        tmp = CACHE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(cat, fh, ensure_ascii=False)
        os.replace(tmp, CACHE)
        return cat
    except Exception as e:  # sin red: seguir con lo último que haya
        log(f'no pude leer el catálogo del homelab: {e}', xbmc.LOGWARNING)
        if os.path.isfile(CACHE):
            with open(CACHE, encoding='utf-8') as fh:
                return json.load(fh)
        return {'peliculas': [], 'series': []}
