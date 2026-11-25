# -*- coding: utf-8 -*-
"""Backup diario de la configuración de este Kodi a una carpeta del homelab (lo hace el servicio de Vidrio).

Arma un zip con lo que hace falta para dejar un Kodi como estaba: ajustes de Kodi (guisettings.xml), orígenes,
favoritos, atajos del control, ajustes de cada add-on y los datos de Vidrio ("Mis canales", posiciones). No guarda
claves: queda afuera la vinculación de Trakt (script.trakt) y passwords.xml, y en los ajustes de los demás add-ons se
vacían (como en guisettings.xml) los que por su nombre son claves o cuentas (sin_claves). Al restaurar, Trakt se vuelve a vincular.

Destino: ajuste "respaldo_destino" (por defecto smb://<homelab>/KodiBackups/), una carpeta por equipo, con los
últimos COPIAS backups.
"""
import os
import re
import time
import zipfile

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon('plugin.video.vidrio')
PERFIL = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
DATOS = xbmcvfs.translatePath('special://userdata')
MARCA = os.path.join(PERFIL, 'ultimo_respaldo')
CADA = 20 * 3600
COPIAS = 14
ARCHIVOS = ['guisettings.xml', 'sources.xml', 'favourites.xml', 'advancedsettings.xml', 'mediasources.xml',
            'profiles.xml', 'RssFeeds.xml', 'upnpserver.xml']
CARPETAS = ['keymaps', 'playlists']
SIN_CLAVES = {'script.trakt'}  # add-ons cuyos ajustes guardan claves de cuentas
DE_VIDRIO = ['mis_canales.json', 'posiciones.json', 'settings.xml']


def log(msg, nivel=xbmc.LOGINFO):
    xbmc.log(f'[vidrio] respaldo: {msg}', nivel)


def destino():
    elegido = ADDON.getSettingString('respaldo_destino').strip()
    if elegido:
        return elegido.rstrip('/') + '/'
    host = re.match(r'smb://([^/]+)/', ADDON.getSettingString('catalogo') or '')
    return f"smb://{host.group(1) if host else '192.168.1.50'}/KodiBackups/"


def equipo():
    """Nombre de la carpeta del equipo. Kodi se llama "Kodi (<IP>)" si no se le puso nombre: la IP puede cambiar, así
    que en ese caso va la plataforma (Android, tvOS, macOS...). Con un nombre propio (Ajustes > Servicios), ese."""
    nombre = re.sub(r'\s*\([^)]*\)\s*$', '', xbmc.getInfoLabel('System.FriendlyName') or '').strip()
    if not nombre or nombre.lower() == 'kodi':
        nombre = next((p for p in ('Android', 'tvOS', 'iOS', 'macOS', 'Windows', 'Linux')
                       if xbmc.getCondVisibility(f'System.Platform.{p.replace("macOS", "OSX")}')), 'Kodi')
    return re.sub(r'[^A-Za-z0-9._-]+', '-', nombre).strip('-') or 'Kodi'


def toca():
    try:
        return time.time() - os.path.getmtime(MARCA) > CADA
    except OSError:
        return True


def contenido():
    """(ruta en el disco, nombre dentro del zip) de lo que se respalda."""
    for nombre in ARCHIVOS:
        ruta = os.path.join(DATOS, nombre)
        if os.path.isfile(ruta):
            yield ruta, nombre
    for carpeta in CARPETAS:
        base = os.path.join(DATOS, carpeta)
        for raiz, _, archivos in os.walk(base):
            for nombre in archivos:
                ruta = os.path.join(raiz, nombre)
                yield ruta, os.path.relpath(ruta, DATOS)
    base = os.path.join(DATOS, 'addon_data')
    if os.path.isdir(base):
        for addon in sorted(os.listdir(base)):
            if addon in SIN_CLAVES:
                continue
            nombres = DE_VIDRIO if addon == 'plugin.video.vidrio' else ['settings.xml']
            for nombre in nombres:
                ruta = os.path.join(base, addon, nombre)
                if os.path.isfile(ruta):
                    yield ruta, os.path.join('addon_data', addon, nombre)


# Una palabra entera del id (separada por . _ -), no un pedazo: "keyboardlayouts" o "avoidclipping" no son claves
CLAVE = re.compile(r'(^|[._-])(token|access_?token|refresh_?token|pass|password|passwd|passphrase|secret|key|api_?key|'
                   r'auth|authorization|login|user|username|cookie|session|credentials?|pin|pincode|lockcode|clave|contrasena)'
                   r'([._-]|$)', re.I)


def sin_claves(xml):
    """Vacía los ajustes de un add-on que parecen claves o cuentas (por su id), en los dos formatos de Kodi."""
    def es_clave(ident, valor):  # un verdadero/falso nunca es una clave ("...switch.user.show", "..._login")
        return CLAVE.search(ident) and valor.strip().lower() not in ('true', 'false', '')
    xml = re.sub(r'(<setting\s+id="([^"]*)"[^>]*?)\s+value="([^"]*)"', lambda m: m.group(1) + ' value=""'
                 if es_clave(m.group(2), m.group(3)) else m.group(0), xml)
    return re.sub(r'(<setting\s+id="([^"]*)"[^>/]*>)([^<]*)(</setting>)', lambda m: m.group(1) + m.group(4)
                  if es_clave(m.group(2), m.group(3)) else m.group(0), xml)


def copiar(origen, destino_zip):
    """xbmcvfs.copy y, si falla, escribiendo el archivo (anda mejor con smb:// y carpetas fuera de Kodi)."""
    if xbmcvfs.copy(origen, destino_zip):
        return True
    with open(origen, 'rb') as fh:
        datos = fh.read()
    f = xbmcvfs.File(destino_zip, 'w')
    try:
        ok = f.write(bytearray(datos))
    finally:
        f.close()
    return bool(ok) and xbmcvfs.exists(destino_zip)


def respaldar(a_donde=None):
    """Hace el backup. Devuelve la ruta de destino o None si no se pudo (se reintenta en la próxima vuelta)."""
    carpeta = (a_donde or destino()).rstrip('/') + '/' + equipo() + '/'
    nombre = f"kodi-{equipo()}-{time.strftime('%Y%m%d-%H%M')}.zip"
    temporal = os.path.join(xbmcvfs.translatePath('special://temp'), nombre)
    with zipfile.ZipFile(temporal, 'w', zipfile.ZIP_DEFLATED) as z:
        for ruta, dentro in contenido():
            if dentro == 'guisettings.xml' or (dentro.startswith('addon_data/') and dentro.endswith('settings.xml')):
                with open(ruta, encoding='utf-8', errors='replace') as fh:
                    z.writestr(dentro, sin_claves(fh.read()))
            else:
                z.write(ruta, dentro)
        z.writestr('LEEME.txt', f"Backup de Kodi ({equipo()}), {time.strftime('%Y-%m-%d %H:%M')}.\n"
                                "Sin claves: hay que volver a vincular Trakt.\n")
    try:
        if not xbmcvfs.exists(carpeta) and not xbmcvfs.mkdirs(carpeta):
            log(f'no puedo crear {carpeta}', xbmc.LOGWARNING)
            return None
        if not copiar(temporal, carpeta + nombre):
            log(f'no pude copiar a {carpeta}', xbmc.LOGWARNING)
            return None
        _, archivos = xbmcvfs.listdir(carpeta)
        viejos = sorted(a for a in archivos if a.startswith('kodi-') and a.endswith('.zip'))[:-COPIAS]
        for viejo in viejos:
            xbmcvfs.delete(carpeta + viejo)
    finally:
        try:
            os.remove(temporal)
        except OSError:
            pass
    os.makedirs(PERFIL, exist_ok=True)
    with open(MARCA, 'w') as fh:
        fh.write(nombre)
    log(f'listo: {carpeta}{nombre}')
    return carpeta + nombre
