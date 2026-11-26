# -*- coding: utf-8 -*-
"""¿Hay una versión de Vidrio más nueva que la instalada? (para avisar si Kodi no se actualiza solo)

Kodi se actualiza desde repository.vidrio, pero en el Apple TV, después de horas dormido en segundo plano, puede
quedarse con un índice viejo del repositorio y no volver a pedirlo hasta que se cierra. El servicio pregunta acá qué
versión publica el homelab y, si Kodi no se pone al día en un rato, avisa que hay que cerrarlo y volver a abrirlo.
"""
import hashlib
import json
import os
import re
import shutil
import time
import urllib.request
import zipfile

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


def notificar(titulo, mensaje, ms=8000):
    xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'GUI.ShowNotification', 'params': {
        'title': titulo, 'message': mensaje, 'displaytime': ms,
        'image': xbmcvfs.translatePath('special://home/addons/plugin.video.vidrio/icon.png')}}))


def _bajar(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Vidrio para Kodi'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def instalar(addon, version):
    """Instala addon-version desde el repositorio de casa sin pasar por Kodi: en el Apple TV (Kodi 22) Kodi revisa el
    repositorio, ve la versión nueva y no la instala. Baja el zip, lo compara con su .sha256, lo descomprime aparte,
    confirma id y versión en su addon.xml y recién ahí reemplaza la carpeta en special://home/addons (si algo falla,
    vuelve la anterior). Después Kodi relee los add-ons (UpdateLocalAddons). Devuelve True si quedó instalada."""
    indice = repositorio()
    if not indice:
        return False
    base = indice.rsplit('/', 1)[0] + '/'
    url = f'{base}{addon}/{addon}-{version}.zip'
    datos = _bajar(url)
    esperado = _bajar(url + '.sha256').decode('ascii', 'replace').split()[0].lower()
    if hashlib.sha256(datos).hexdigest() != esperado:
        raise ValueError(f'{addon}-{version}.zip no coincide con su sha256')
    temporal = xbmcvfs.translatePath('special://temp/')
    nuevo = os.path.join(temporal, f'vidrio-nuevo-{addon}')
    shutil.rmtree(nuevo, ignore_errors=True)
    zip_local = nuevo + '.zip'
    with open(zip_local, 'wb') as fh:
        fh.write(datos)
    try:
        with zipfile.ZipFile(zip_local) as z:
            for nombre in z.namelist():  # solo archivos dentro de la carpeta del add-on
                if not nombre.startswith(addon + '/') or '..' in nombre.split('/'):
                    raise ValueError(f'ruta inesperada en el zip: {nombre}')
            z.extractall(nuevo)
    finally:
        os.remove(zip_local)
    carpeta_nueva = os.path.join(nuevo, addon)
    with open(os.path.join(carpeta_nueva, 'addon.xml'), encoding='utf-8') as fh:
        cabecera = re.search(r'<addon\s[^>]*>', fh.read()).group(0)
    if f'id="{addon}"' not in cabecera or f'version="{version}"' not in cabecera:
        raise ValueError(f'el addon.xml del zip no es {addon} {version}')
    destino = os.path.join(xbmcvfs.translatePath('special://home/addons/'), addon)
    viejo = os.path.join(temporal, f'vidrio-viejo-{addon}-{int(time.time())}')
    tenia = os.path.isdir(destino)
    if tenia:
        shutil.move(destino, viejo)
    try:
        shutil.move(carpeta_nueva, destino)
    except Exception:
        if tenia:
            shutil.rmtree(destino, ignore_errors=True)
            shutil.move(viejo, destino)
        raise
    finally:
        shutil.rmtree(nuevo, ignore_errors=True)
    if tenia:
        shutil.rmtree(viejo, ignore_errors=True)
    xbmc.executebuiltin('UpdateLocalAddons')
    if addon == xbmc.getSkinDir():
        xbmc.executebuiltin('ReloadSkin()')
    xbmc.log(f'[vidrio.version] instalado {addon} {version} desde {base}', xbmc.LOGINFO)
    return True
