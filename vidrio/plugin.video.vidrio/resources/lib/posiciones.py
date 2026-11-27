# -*- coding: utf-8 -*-
"""Dónde quedó cada película o episodio del homelab en este equipo (lo anota el servicio al cortar).

Trakt da por vista una película o un episodio que se corta pasado el 80 % y lo saca de "Continuar viendo" aunque
falten minutos, y Kodi no guarda su punto pasado el 92 % (en un episodio de media hora, los créditos). Con lo que anota
este equipo, volver a abrirlo lo retoma donde se cortó, desde "Continuar viendo" o desde la lista de la serie, salvo
que haya terminado: los últimos FINAL segundos (lo que dura el cartel del siguiente episodio) o el final del video.
"""
import json
import os
import time

import xbmcaddon
import xbmcvfs

PERFIL = xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.vidrio').getAddonInfo('profile'))
ARCHIVO = os.path.join(PERFIL, 'posiciones.json')
MINIMO = 120          # segundos: menos que esto no es "empezado"
FINAL = 20            # segundos: si quedan menos, lo terminó (el cartel del siguiente episodio sale a los 15)
CASI = 0.95           # pasado esto (los créditos), "Continuar viendo" ofrece el siguiente episodio en vez de este
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
    """Anota dónde quedó, lo borra si lo terminó y no toca nada si apenas lo empezó (abrirlo desde el principio y
    cortarlo enseguida no borra el punto que ya tenía). Devuelve el porcentaje anotado o None."""
    if not archivo or not total or total <= 0:
        return None
    if posicion < MINIMO:
        return None
    datos = cargar()
    porcentaje = posicion / total
    if total - posicion <= FINAL:
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


def punto(archivo, datos=None):
    """(posición, total) anotados para el archivo, o None."""
    d = (cargar() if datos is None else datos).get(archivo)
    if not d or not d.get('total'):
        return None
    return float(d.get('posicion') or 0), float(d['total'])
