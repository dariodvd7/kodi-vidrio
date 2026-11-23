# -*- coding: utf-8 -*-
"""Lo que Trakt sabe de la cuenta vinculada en el add-on oficial (script.trakt): reproducciones a medias y lista.

No pide otra vinculación: usa el token que guardó script.trakt y su identificador de cliente. Las respuestas se guardan
un rato en el perfil de Vidrio para no consultar Trakt en cada pantalla; borrar() las invalida (al terminar de ver algo).
"""
import json
import os
import re
import time
import urllib.request

import xbmc
import xbmcaddon
import xbmcvfs

PERFIL = xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.vidrio').getAddonInfo('profile'))
API = 'https://api.trakt.tv'
VIGENCIA = {'playback': 60, 'watchlist': 600}


def log(msg, nivel=xbmc.LOGINFO):
    xbmc.log(f'[vidrio] trakt: {msg}', nivel)


def credenciales():
    """(client_id, access_token) de script.trakt, o None si no está instalado o vinculado."""
    if not xbmc.getCondVisibility('System.HasAddon(script.trakt)'):  # sin error "Unknown addon id" en el log
        return None
    try:
        addon = xbmcaddon.Addon('script.trakt')
    except RuntimeError:
        return None
    try:
        token = json.loads(addon.getSetting('authorization') or '{}').get('access_token')
    except ValueError:
        token = None
    if not token:
        return None
    ruta = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('path')), 'resources', 'lib', 'traktapi.py')
    try:
        with open(ruta, encoding='utf-8') as fh:
            m = re.search(r'__client_id: str = \[([0-9, ]+)\]', fh.read())
    except OSError:
        m = None
    if not m:
        return None
    client_id = ''.join(chr(int(b) ^ 0x42) for b in m.group(1).split(','))
    return client_id, token


def _cache(nombre):
    return os.path.join(PERFIL, f'trakt_{nombre}.json')


def _pedir(nombre, ruta):
    archivo = _cache(nombre)
    if os.path.isfile(archivo) and time.time() - os.path.getmtime(archivo) < VIGENCIA[nombre]:
        with open(archivo, encoding='utf-8') as fh:
            return json.load(fh)
    cred = credenciales()
    if not cred:
        return []
    req = urllib.request.Request(API + ruta, headers={
        'Content-Type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': cred[0],
        'Authorization': f'Bearer {cred[1]}', 'User-Agent': 'Vidrio para Kodi'})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            datos = json.loads(r.read().decode('utf-8'))
    except Exception as e:  # sin red o token vencido (script.trakt lo renueva en su próxima llamada)
        log(f'no pude leer {ruta}: {e}', xbmc.LOGWARNING)
        if os.path.isfile(archivo):
            with open(archivo, encoding='utf-8') as fh:
                return json.load(fh)
        return []
    os.makedirs(PERFIL, exist_ok=True)
    with open(archivo, 'w', encoding='utf-8') as fh:
        json.dump(datos, fh)
    return datos


def reproducciones():
    """Películas y episodios a medias, el más reciente primero."""
    datos = _pedir('playback', '/sync/playback?limit=50')
    return sorted(datos, key=lambda x: x.get('paused_at', ''), reverse=True)


def lista():
    """Películas y series de la lista de seguimiento (watchlist), la última agregada primero."""
    datos = [x for x in _pedir('watchlist', '/sync/watchlist') if x.get('type') in ('movie', 'show')]
    return sorted(datos, key=lambda x: x.get('listed_at', ''), reverse=True)


def borrar():
    for nombre in VIGENCIA:
        try:
            os.remove(_cache(nombre))
        except OSError:
            pass
