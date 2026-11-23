# -*- coding: utf-8 -*-
"""Guía de TV (guia.json del homelab, armada por homelab/guia.py) para la ventana Guía de la skin.

El archivo está al lado del catálogo (misma carpeta que el ajuste 'catalogo'). Se guarda 10 minutos en el perfil.
"""
import json
import os
import time

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon('plugin.video.vidrio')
PERFIL = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
CACHE = os.path.join(PERFIL, 'guia.json')
VIGENCIA = 10 * 60


def log(msg, nivel=xbmc.LOGINFO):
    xbmc.log(f'[vidrio] guía: {msg}', nivel)


def ruta_remota():
    catalogo = ADDON.getSettingString('catalogo')
    return catalogo.rsplit('/', 1)[0] + '/guia.json'


def cargar():
    if os.path.isfile(CACHE) and time.time() - os.path.getmtime(CACHE) < VIGENCIA:
        with open(CACHE, encoding='utf-8') as fh:
            return json.load(fh)
    try:
        with xbmcvfs.File(ruta_remota()) as fh:
            datos = fh.readBytes()
        if not datos:
            raise IOError('vacía o inaccesible')
        guia = json.loads(bytes(datos).decode('utf-8'))
        os.makedirs(PERFIL, exist_ok=True)
        with open(CACHE + '.tmp', 'w', encoding='utf-8') as fh:
            json.dump(guia, fh, ensure_ascii=False)
        os.replace(CACHE + '.tmp', CACHE)
        return guia
    except Exception as e:
        log(f'no pude leer la guía del homelab: {e}', xbmc.LOGWARNING)
        if os.path.isfile(CACHE):
            with open(CACHE, encoding='utf-8') as fh:
                return json.load(fh)
        return {'grupos': [], 'canales': []}


def hora(t):
    return time.strftime('%H:%M', time.localtime(t))


def ahora_y_despues(canal, ahora=None):
    """(programa al aire o None, siguiente o None)."""
    ahora = ahora or time.time()
    actual = siguiente = None
    for p in canal.get('programas', []):
        if p['inicio'] <= ahora < p['fin']:
            actual = p
        elif p['inicio'] >= ahora:
            siguiente = p
            break
    return actual, siguiente


# Página de cada canal en DGO (dtvmobile://dgo/home/lander/<clave>). Las claves las arma el CMS de DGO; las de marca
# están en la web (landerUris en su JS) y distinguen mayúsculas. Se probaron en directvgo.com con sesión iniciada:
# HBO, Universal y DISCOVERY muestran sus canales en vivo (Lionsgate solo películas). Una clave inexistente muestra
# "¡Ups! Algo pasó" (M2-1998; pasó con "espnpremium" y "tntsportspremium"). Sin clave, el canal abre TV en vivo.
CLAVES_DGO = {
    'Universal Channel': 'Universal',
    'Discovery Channel': 'DISCOVERY', 'Discovery Turbo': 'DISCOVERY', 'Discovery World': 'DISCOVERY',
    'Discovery Home And Health': 'DISCOVERY', 'Animal Planet': 'DISCOVERY', 'Discovery Kids': 'DISCOVERY',
}


def clave_dgo(nombre):
    if nombre.startswith('HBO'):  # la página HBO trae HBO, HBO 2, HBO Family y HBO Signature en vivo
        return 'HBO'
    return CLAVES_DGO.get(nombre, '')
