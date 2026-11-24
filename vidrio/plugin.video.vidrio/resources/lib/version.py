# -*- coding: utf-8 -*-
"""¿Hay una versión de Vidrio más nueva que la instalada? (para avisar si Kodi no se actualiza solo)

Kodi se actualiza desde repository.vidrio, pero en el Apple TV, después de horas dormido en segundo plano, puede
quedarse con un índice viejo del repositorio y no volver a pedirlo hasta que se cierra. El servicio pregunta acá qué
versión publica el homelab y, si Kodi no se pone al día en un rato, avisa que hay que cerrarlo y volver a abrirlo.
"""
import json
import re
import urllib.request

import xbmc
import xbmcaddon
import xbmcvfs

ADDONS = {'plugin.video.vidrio': 'plugin', 'skin.vidrio': 'skin'}


def repositorio():
    """Dirección del índice (addons.xml) según el repository.vidrio instalado, o None."""
    ruta = xbmcvfs.translatePath('special://home/addons/repository.vidrio/addon.xml')
    try:
        with open(ruta, encoding='utf-8') as fh:
            m = re.search(r'<info[^>]*>([^<]+)</info>', fh.read())
        return m.group(1).strip() if m else None
    except OSError:
        return None


def numero(v):
    return tuple(int(x) for x in re.findall(r'\d+', v or '0'))


def publicadas():
    url = repositorio()
    if not url:
        return {}
    req = urllib.request.Request(url, headers={'User-Agent': 'Vidrio para Kodi'})
    with urllib.request.urlopen(req, timeout=8) as r:
        indice = r.read().decode('utf-8', 'replace')
    salida = {}
    for addon in ADDONS:
        m = re.search(rf'<addon\s[^>]*id="{re.escape(addon)}"[^>]*>', indice)
        v = m and re.search(r'version="([^"]+)"', m.group(0))
        if v:
            salida[addon] = v.group(1)
    return salida


def instalada(addon):
    try:
        return xbmcaddon.Addon(addon).getAddonInfo('version')
    except RuntimeError:
        return None


def pendientes(publicado):
    """[(add-on, instalada, publicada)] de lo que está atrasado."""
    salida = []
    for addon, pub in publicado.items():
        inst = instalada(addon)
        if inst and numero(pub) > numero(inst):
            salida.append((addon, inst, pub))
    return salida


def avisar(atrasados):
    """Por JSON-RPC (GUI.ShowNotification): Dialog().notification no muestra nada cuando el plugin corre sin ventana
    propia (probado en el TCL); el pedido de Kodi aparece siempre."""
    pub = max((p for _, _, p in atrasados), key=numero)
    xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'GUI.ShowNotification', 'params': {
        'title': f'Hay una versión nueva de Vidrio ({pub})',
        'message': 'Cerrá Kodi desde Apagar > Salir y volvé a abrirlo para actualizar.',
        'image': xbmcvfs.translatePath('special://home/addons/plugin.video.vidrio/icon.png'),
        'displaytime': 12000}}))
