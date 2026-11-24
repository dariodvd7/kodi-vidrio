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
MIS_CANALES = os.path.join(PERFIL, 'mis_canales.json')
# "Mis canales" antes de elegirlos: los de aire, noticias y deportes más vistos (por nombre en la guía)
MIS_INICIALES = ['Telefe', 'El Trece', 'America TV', 'TV Publica', 'TN', 'C5N', 'ESPN', 'ESPN Premium', 'TNT Sports',
                 'TYC Sports', 'Fox Sports']


def log(msg, nivel=xbmc.LOGINFO):
    xbmc.log(f'[vidrio] guía: {msg}', nivel)


def ruta_remota():
    catalogo = ADDON.getSettingString('catalogo')
    return catalogo.rsplit('/', 1)[0] + '/guia.json'


def cargar():
    from resources.lib import copia
    if os.path.isfile(CACHE) and time.time() - os.path.getmtime(CACHE) < VIGENCIA:
        guia = copia.leer(CACHE)
        if guia is not None:
            return guia
    try:
        with xbmcvfs.File(ruta_remota()) as fh:
            datos = fh.readBytes()
        if not datos:
            raise IOError('vacía o inaccesible')
        guia = json.loads(bytes(datos).decode('utf-8'))
        copia.escribir(CACHE, guia)
        return guia
    except Exception as e:
        log(f'no pude leer la guía del homelab: {e}', xbmc.LOGWARNING)
        return copia.leer(CACHE) or {'grupos': [], 'canales': []}


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
    # plugin 1.9.0 (tocando cada canal en la grilla de la web; muestras confirmadas en su ficha)
    'A&E': '064', 'Adult Swim': '039', 'AMC': '068', 'Animal Planet': '074', 'Antena3': '075', 'Atres Series': '076',
    'Baby TV': '085', 'Canal A': '094', 'Cartoon Network': '098', 'Cartoonito': '087', 'Cinemax': '107',
    'CNN Español': '111', 'CNN Internacional': '112', 'Comedy Central': '114', 'Daystar': '410', 'Deportv': '010',
    'Discovery Channel': '020', 'Discovery Home & Health': '015', 'Discovery ID': '117', 'Discovery Kids': '142',
    'Discovery Theater': '118', 'Discovery World': '119', 'Disney Channel': '141', 'Disney Junior': '146',
    'E! Entertainment': '149', 'El Gourmet': '151', 'Encuentro': '155', 'F24': '420', 'Food Network': '171',
    'Hgtv': '203', 'History 2': '019', 'History Channel': '202', 'Lifetime': '215', 'Magazine': '211', 'MTV': '222',
    'Nat Geo': '223', 'Nick Jr': '226', 'Nickelodeon': '229', 'Plim Plim': '421', 'Space': '246', 'TLC': '050',
    'TNT Novelas': '053', 'Universal Channel': '031',
}
PAGINAS_DGO = {}  # Universal y Discovery ya abren directo; HBO no está en el plan (su página dice "Quiero verlo")


def destino_dgo(nombre):
    if nombre in CANALES_DGO:
        return f'player/live/CH0100000000{CANALES_DGO[nombre]}'
    if nombre.startswith('HBO'):  # la página HBO trae HBO, HBO 2, HBO Family y HBO Signature en vivo
        return 'home/lander/HBO'
    return f'home/lander/{PAGINAS_DGO[nombre]}' if nombre in PAGINAS_DGO else ''


def mis_canales(guia=None):
    """Identificadores de "Mis canales" en el orden elegido (cada equipo guarda los suyos en el perfil del plugin)."""
    try:
        with open(MIS_CANALES, encoding='utf-8') as fh:
            return [str(i) for i in json.load(fh)]
    except (OSError, ValueError):
        por_nombre = {c['nombre']: c['id'] for c in (guia or cargar()).get('canales', [])}
        return [por_nombre[n] for n in MIS_INICIALES if n in por_nombre]


def guardar_mis_canales(ids):
    from resources.lib import copia
    copia.escribir(MIS_CANALES, list(ids))
