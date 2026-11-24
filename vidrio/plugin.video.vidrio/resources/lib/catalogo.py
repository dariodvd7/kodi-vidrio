# -*- coding: utf-8 -*-
"""Lee el catálogo del homelab y lo guarda en caché local (o el de carpetas.py, si el origen es Carpetas)."""
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
    from resources.lib import copia, carpetas
    if carpetas.activo():  # sin homelab: el catálogo que arman carpetas.escanear() (el servicio, cada 12 horas)
        return carpetas.leer() or {'peliculas': [], 'series': []}
    fresco = os.path.isfile(CACHE) and time.time() - os.path.getmtime(CACHE) < VIGENCIA
    if fresco and not forzar:
        cat = copia.leer(CACHE)
        if cat is not None:
            return cat
    try:
        cat = _leer_remoto()
        copia.escribir(CACHE, cat)
        return cat
    except Exception as e:  # sin red: seguir con lo último que haya
        log(f'no pude leer el catálogo del homelab: {e}', xbmc.LOGWARNING)
        return copia.leer(CACHE) or {'peliculas': [], 'series': []}
