# -*- coding: utf-8 -*-
"""Restaurar un backup de la configuración de Kodi (los que arma respaldo.py), desde los ajustes de Vidrio.

Kodi tiene sus ajustes (guisettings.xml) y los de la skin en memoria y los escribe al cerrarse: copiar esos archivos
no sirve, Kodi los pisaría. Por eso se aplican con Kodi abierto (JSON-RPC Settings.* y Skin.SetBool/SetString) y Kodi
los guarda al salir. Lo demás se copia: orígenes, favoritos, atajos del control, listas, ajustes de los add-ons y los
datos de Vidrio. Los ajustes de un add-on que son claves (respaldo.CLAVE) no vienen en el backup: se conservan los que
tenga este equipo. Tampoco se tocan los ajustes de hardware (pantalla, frecuencia, salida de audio): el backup puede
ser de otro equipo. Al final hay que salir de Kodi para que guarde todo, y volver a vincular Trakt.
"""
import json
import os
import re
import shutil
import tempfile
import time
import zipfile

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import respaldo

DATOS = xbmcvfs.translatePath('special://userdata')
NO_TOCAR = ('videoscreen.', 'audiooutput.audiodevice', 'audiooutput.passthroughdevice', 'audiooutput.channels',
            'videoplayer.adjustrefreshrate', 'videoplayer.usedisplayasclock', 'debug.', 'services.devicename',
            'services.deviceuuid', 'system.', 'network.', 'filecache.', 'input.appleremote', 'peripherals.')
COPIAR = respaldo.ARCHIVOS[1:]  # todo menos guisettings.xml, que va por JSON-RPC


def log(msg, nivel=xbmc.LOGINFO):
    xbmc.log(f'[vidrio] restaurar: {msg}', nivel)


def rpc(metodo, **params):
    r = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': metodo, 'params': params})))
    return r.get('result'), r.get('error')


def backups():
    """{equipo: [zips, el más nuevo primero]} en la carpeta de backups."""
    base = respaldo.destino()
    salida = {}
    carpetas, _ = xbmcvfs.listdir(base)
    for equipo in sorted(carpetas):
        _, archivos = xbmcvfs.listdir(base + equipo + '/')
        zips = sorted((a for a in archivos if a.startswith('kodi-') and a.endswith('.zip')), reverse=True)
        if zips:
            salida[equipo] = [base + equipo + '/' + z for z in zips]
    return salida


def fecha(ruta):
    m = re.search(r'-(\d{8})-(\d{4})\.zip$', ruta)
    if not m:
        return os.path.basename(ruta)
    d, h = m.groups()
    return f'{d[6:8]}/{d[4:6]}/{d[:4]} {h[:2]}:{h[2:]}'


def _ajustes_xml(texto):
    """[(id, valor o None si está en su valor de fábrica, atributos)] de un settings.xml o guisettings.xml."""
    salida = []
    for m in re.finditer(r'<setting\s+([^>]*?)(/>|>(.*?)</setting>)', texto, re.S):
        atributos = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if 'id' not in atributos:
            continue
        valor = atributos.get('value') if 'value' in atributos else (m.group(3) or '')
        de_fabrica = atributos.get('default') == 'true'
        salida.append((atributos['id'], None if de_fabrica else _xml_a_texto(valor), atributos))
    return salida


def _xml_a_texto(v):
    return (v.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&apos;', "'")
            .replace('&amp;', '&'))


def _como_tipo(actual, texto):
    if isinstance(actual, bool):
        return texto.strip().lower() == 'true'
    if isinstance(actual, int):
        return int(float(texto))
    if isinstance(actual, float):
        return float(texto)
    if isinstance(actual, list):
        return [x for x in texto.split(',') if x] if texto else []  # Kodi guarda las listas separadas por coma
    return texto


def aplicar_kodi(texto, prueba):
    """Ajustes de guisettings.xml por JSON-RPC. Devuelve cuántos cambió."""
    cambios = 0
    try:  # los que hoy no están de fábrica en este equipo (lo último que guardó Kodi)
        with open(os.path.join(DATOS, 'guisettings.xml'), encoding='utf-8', errors='replace') as fh:
            cambiados_hoy = {i for i, v, _ in _ajustes_xml(fh.read()) if v is not None}
    except OSError:
        cambiados_hoy = set()
    for ident, valor, _ in _ajustes_xml(texto):
        if ident.startswith(NO_TOCAR) or respaldo.CLAVE.search(ident):
            continue
        actual, error = rpc('Settings.GetSettingValue', setting=ident)
        if error or actual is None:
            continue
        actual = actual.get('value')
        try:
            if valor is None:  # en el backup está de fábrica: volver a fábrica si acá se cambió
                if ident in cambiados_hoy:
                    log(f'{ident}: a fábrica')
                    if not prueba:
                        rpc('Settings.ResetSettingValue', setting=ident)
                    cambios += 1
                continue
            nuevo = _como_tipo(actual, valor)
            if nuevo == actual:
                continue
            log(f'{ident}: {actual!r} -> {nuevo!r}')
            if not prueba:
                _, err = rpc('Settings.SetSettingValue', setting=ident, value=nuevo)
                if err:
                    log(f'{ident}: {err.get("message")}')
                    continue
            cambios += 1
        except (ValueError, TypeError):
            continue
    return cambios


def aplicar_skin(texto, prueba):
    """Ajustes de la skin con los comandos de Kodi (los guarda al salir)."""
    cambios = 0
    for ident, valor, atributos in _ajustes_xml(texto):
        tipo = atributos.get('type', 'string')
        actual = xbmc.getInfoLabel(f'Skin.String({ident})') if tipo == 'string' else \
            ('true' if xbmc.getCondVisibility(f'Skin.HasSetting({ident})') else 'false')
        valor = valor if valor is not None else ('false' if tipo == 'bool' else '')
        if valor == actual:
            continue
        cambios += 1
        if prueba:
            continue
        if tipo == 'bool':
            xbmc.executebuiltin(f'Skin.SetBool({ident})' if valor == 'true' else f'Skin.Reset({ident})')
        elif valor:
            xbmc.executebuiltin(f'Skin.SetString({ident},"{valor.replace(chr(34), chr(92) + chr(34))}")')
        else:
            xbmc.executebuiltin(f'Skin.Reset({ident})')
    return cambios


def fusionar_addon(nuevo, ruta_actual):
    """settings.xml del backup, con las claves que tenga hoy este equipo (el backup las trae vacías)."""
    if not os.path.isfile(ruta_actual):
        return nuevo
    with open(ruta_actual, encoding='utf-8', errors='replace') as fh:
        texto = fh.read()
    crudos = {}  # id -> valor tal cual en el archivo de hoy (aunque sea el de fábrica)
    for m in re.finditer(r'<setting\s+([^>]*?)(/>|>(.*?)</setting>)', texto, re.S):
        atributos = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if 'id' in atributos:
            crudos[atributos['id']] = atributos['value'] if 'value' in atributos else (m.group(3) or '')

    def poner(m):
        ident = re.search(r'id="([^"]*)"', m.group(0)).group(1)
        vacio = re.search(r'value=""', m.group(0)) or re.search(r'>\s*</setting>', m.group(0)) or m.group(0).endswith('/>')
        if not respaldo.CLAVE.search(ident) or not vacio or not crudos.get(ident):
            return m.group(0)
        valor = crudos[ident]  # ya viene escapado del XML de hoy
        if 'value="' in m.group(0):
            return re.sub(r'value="[^"]*"', f'value="{valor}"', m.group(0))
        return re.sub(r'>[^<]*</setting>', f'>{valor}</setting>', m.group(0))
    return re.sub(r'<setting\s+[^>]*?(?:/>|>[^<]*</setting>)', poner, nuevo)


def restaurar(ruta_zip, prueba=False):
    """Restaura (o, con prueba, solo cuenta lo que cambiaría). Devuelve un resumen."""
    temporal = tempfile.mkdtemp(dir=xbmcvfs.translatePath('special://temp'))
    try:
        local = os.path.join(temporal, 'backup.zip')
        if not xbmcvfs.copy(ruta_zip, local):
            f = xbmcvfs.File(ruta_zip)
            try:
                datos = bytes(f.readBytes())
            finally:
                f.close()
            if not datos:
                raise IOError(f'no pude bajar {ruta_zip}')
            with open(local, 'wb') as fh:
                fh.write(datos)
        carpeta = os.path.join(temporal, 'x')
        with zipfile.ZipFile(local) as z:
            for nombre in z.namelist():  # nada fuera de la carpeta (rutas con .. o absolutas)
                if nombre.startswith('/') or '..' in nombre.split('/'):
                    raise ValueError(f'ruta inválida en el backup: {nombre}')
            z.extractall(carpeta)
        resumen = {'kodi': 0, 'skin': 0, 'archivos': 0, 'add-ons': 0}
        gui = os.path.join(carpeta, 'guisettings.xml')
        if os.path.isfile(gui):
            with open(gui, encoding='utf-8', errors='replace') as fh:
                resumen['kodi'] = aplicar_kodi(fh.read(), prueba)
        skin = xbmc.getSkinDir()
        archivo_skin = os.path.join(carpeta, 'addon_data', skin, 'settings.xml')
        if os.path.isfile(archivo_skin):
            with open(archivo_skin, encoding='utf-8', errors='replace') as fh:
                resumen['skin'] = aplicar_skin(fh.read(), prueba)
        for nombre in COPIAR + respaldo.CARPETAS:
            origen = os.path.join(carpeta, nombre)
            if not os.path.exists(origen):
                continue
            resumen['archivos'] += 1
            if prueba:
                continue
            destino = os.path.join(DATOS, nombre)
            if os.path.isdir(origen):
                shutil.copytree(origen, destino, dirs_exist_ok=True)
            else:
                shutil.copy2(origen, destino)
        base = os.path.join(carpeta, 'addon_data')
        for addon in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            if addon == skin:
                continue
            for nombre in os.listdir(os.path.join(base, addon)):
                origen = os.path.join(base, addon, nombre)
                destino = os.path.join(DATOS, 'addon_data', addon, nombre)
                if not os.path.isdir(os.path.join(DATOS, 'addons', addon)) and not \
                        xbmc.getCondVisibility(f'System.HasAddon({addon})'):
                    continue  # add-on que este equipo no tiene
                resumen['add-ons'] += 1
                if prueba:
                    continue
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                if nombre == 'settings.xml':
                    with open(origen, encoding='utf-8', errors='replace') as fh:
                        texto = fusionar_addon(fh.read(), destino)
                    with open(destino, 'w', encoding='utf-8') as fh:
                        fh.write(texto)
                else:
                    shutil.copy2(origen, destino)
        log(('prueba: ' if prueba else '') + json.dumps(resumen))
        return resumen
    finally:
        shutil.rmtree(temporal, ignore_errors=True)


def dialogo():
    """El botón "Restaurar un backup" de los ajustes de Vidrio."""
    d = xbmcgui.Dialog()
    try:
        todos = backups()
    except Exception as e:
        log(f'no pude leer la carpeta de backups: {e}', xbmc.LOGWARNING)
        todos = {}
    if not todos:
        d.ok('Restaurar un backup', f'No encontré backups en {respaldo.destino()}.')
        return
    equipo = respaldo.equipo()
    equipos = sorted(todos, key=lambda e: (e != equipo, e))
    if len(equipos) > 1:
        i = d.select('¿De qué equipo?', [f'{e} (este equipo)' if e == equipo else e for e in equipos])
        if i < 0:
            return
        equipo = equipos[i]
    else:
        equipo = equipos[0]
    zips = todos[equipo]
    i = d.select(f'Backup de {equipo}', [fecha(z) for z in zips])
    if i < 0:
        return
    if not d.yesno('Restaurar un backup',
                   f'Se van a restaurar los ajustes de Kodi, la skin, los orígenes, los favoritos y los add-ons del '
                   f'backup del {fecha(zips[i])}.[CR]Después hay que salir de Kodi para terminar y volver a vincular '
                   f'Trakt. ¿Seguimos?'):
        return
    progreso = xbmcgui.DialogProgress()
    progreso.create('Restaurar un backup', 'Aplicando el backup…')
    try:
        resumen = restaurar(zips[i])
    except Exception as e:
        progreso.close()
        log(f'error: {e}', xbmc.LOGWARNING)
        d.ok('Restaurar un backup', f'No se pudo restaurar: {e}')
        return
    progreso.close()
    if d.yesno('Restaurar un backup',
               f"Listo: {resumen['kodi']} ajustes de Kodi, {resumen['skin']} de la skin, {resumen['archivos']} archivos "
               f"y {resumen['add-ons']} de add-ons.[CR]Kodi tiene que cerrarse para guardar todo. Volvé a abrirlo y "
               f"vinculá Trakt. ¿Cerrar Kodi ahora?", nolabel='Después', yeslabel='Cerrar Kodi'):
        time.sleep(1)
        xbmc.executebuiltin('Quit')
