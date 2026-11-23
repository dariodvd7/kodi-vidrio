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


# Destino de cada canal en DGO, como ruta de dtvmobile://dgo/<ruta> (DeepLinkKt.processDeepLink en la app de Android).
# - player/live/<id>: abre el canal directo. Los id (CH01…) salen de la web de DGO con sesión iniciada: la dirección al
#   tocar el canal en su grilla (/player/live/<id>), confirmada en su ficha (/home/pdp/live/<id>). Son de Argentina.
# - home/lander/<clave>: página de marca con sus canales en vivo. Claves de landerUris en el JS de la web; distinguen
#   mayúsculas (HBO, Universal, DISCOVERY). Una clave inexistente da "¡Ups! Algo pasó" (M2-1998).
# Sin destino, el canal abre TV en vivo.
CANALES_DGO = {
    'Telefe': '051', 'El Trece': '152', 'America TV': '071', 'TV Publica': '214', 'TN': '048', 'C5N': '089',
    'ESPN': '162', 'ESPN Premium': '182', 'TNT Sports': '040', 'TYC Sports': '036', 'Fox Sports': '177',
    'Fox Sports Argentina': '177', 'Fox Sports 2': '335', 'Discovery Turbo': '140',
    # plugin 1.4.1
    'ESPN 2': '016', 'ESPN 3': '163', 'ESPN 4': '161', 'Fox Sports 3': '336',
    'A24': '070', 'America 24': '070',  # A24 es América 24: en DGO, "AMERICA 24"
    'La Nacion+': '210', 'LN+': '210', 'El Nueve': '093', 'Cronica TV': '116', 'Canal 26': '092',
    'TNT': '046', 'TNT Series': '044', 'Warner Channel': '026', 'Star Channel': '249', 'AXN': '080', 'Sony': '247',
    'FX': '186',  # en DGO, "FX Colombia"
    'Cinecanal': '104',  # en DGO, "Cinecanal Colombia"
}
PAGINAS_DGO = {
    'Universal Channel': 'Universal',
    'Discovery Channel': 'DISCOVERY', 'Discovery World': 'DISCOVERY', 'Discovery Home And Health': 'DISCOVERY',
    'Animal Planet': 'DISCOVERY', 'Discovery Kids': 'DISCOVERY',
}


def destino_dgo(nombre):
    if nombre in CANALES_DGO:
        return f'player/live/CH0100000000{CANALES_DGO[nombre]}'
    if nombre.startswith('HBO'):  # la página HBO trae HBO, HBO 2, HBO Family y HBO Signature en vivo
        return 'home/lander/HBO'
    return f'home/lander/{PAGINAS_DGO[nombre]}' if nombre in PAGINAS_DGO else ''
