# -*- coding: utf-8 -*-
"""Dónde quedó cada película o episodio del homelab en este equipo (lo anota el servicio al cortar).

Trakt da por vista una película o un episodio que se corta pasado el 80 % y lo saca de "Continuar viendo" aunque
falten minutos. Con lo que anota este equipo, "Continuar viendo" lo sigue mostrando hasta terminarlo (95 %). Kodi
guarda su propio punto, pero bajo la dirección exacta con la que arrancó (que incluye el porcentaje de Trakt) y desde
la lista no se puede encontrar.
"""
import json
import os
import time

import xbmcaddon
import xbmcvfs

PERFIL = xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.vidrio').getAddonInfo('profile'))
ARCHIVO = os.path.join(PERFIL, 'posiciones.json')
MINIMO = 120          # segundos: menos que esto no es "empezado"
TERMINADO = 0.95      # desde acá cuenta como visto
VIGENCIA = 60 * 86400  # se olvidan a los 60 días
MAXIMO = 50


def cargar():
    try:
        with open(ARCHIVO, encoding='utf-8') as fh:
            datos = json.load(fh)
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def anotar(archivo, posicion, total):
    """Anota dónde quedó (o lo borra si lo terminó o apenas lo empezó). Devuelve el porcentaje o None."""
    if not archivo or not total or total <= 0:
        return None
    datos = cargar()
    porcentaje = posicion / total
    if posicion < MINIMO or porcentaje >= TERMINADO:
        datos.pop(archivo, None)
        porcentaje = None
    else:
        datos[archivo] = {'posicion': round(posicion, 1), 'total': round(total, 1), 'cuando': int(time.time())}
    ahora = time.time()
    vigentes = sorted(((a, d) for a, d in datos.items() if ahora - d.get('cuando', 0) < VIGENCIA),
                      key=lambda x: x[1].get('cuando', 0), reverse=True)[:MAXIMO]
    os.makedirs(PERFIL, exist_ok=True)
    with open(ARCHIVO + '.tmp', 'w', encoding='utf-8') as fh:
        json.dump(dict(vigentes), fh)
    os.replace(ARCHIVO + '.tmp', ARCHIVO)
    return porcentaje
