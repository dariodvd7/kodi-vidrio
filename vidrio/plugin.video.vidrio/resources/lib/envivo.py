# -*- coding: utf-8 -*-
"""Partidos para las filas "Deportes en vivo" y "Próximos partidos" del inicio (partidos.json del homelab, armado por
homelab/partidos.py cada 2 minutos: Primera División, Copa Argentina, Libertadores, Sudamericana y NFL).

El servicio de Vidrio lo baja cada minuto mientras el inicio está en pantalla (actualizar) y, si cambió algo (un gol,
el minuto, un partido que empieza o termina), cambia Window(home).Property(Vidrio.EnVivo): la skin recarga la fila,
que lee la copia local (items). Solo se muestran los partidos que la guía ubica en un canal.
"""
import hashlib
import json
import os
import re
import time

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon('plugin.video.vidrio')
PERFIL = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
CACHE = os.path.join(PERFIL, 'partidos.json')
VENCE = 10 * 60  # si el homelab dejó de actualizarlo, la fila no muestra partidos viejos


def log(msg, nivel=xbmc.LOGINFO):
    xbmc.log(f'[vidrio] en vivo: {msg}', nivel)


def ruta_remota():
    return ADDON.getSettingString('catalogo').rsplit('/', 1)[0] + '/partidos.json'


def huella(datos):
    cambia = [datos.get('partidos', []), datos.get('proximos', [])]
    return hashlib.md5(json.dumps(cambia, sort_keys=True).encode('utf-8')).hexdigest()[:12]


def actualizar():
    """Baja partidos.json del homelab. Devuelve la huella de los partidos si cambiaron, si no None."""
    from resources.lib import copia
    try:
        with xbmcvfs.File(ruta_remota()) as fh:
            crudo = fh.readBytes()
        if not crudo:
            raise IOError('vacío o inaccesible')
        datos = json.loads(bytes(crudo).decode('utf-8'))
    except Exception as e:
        log(f'no pude leer los partidos del homelab: {e}', xbmc.LOGDEBUG)
        return None
    anterior = copia.leer(CACHE) or {}
    if anterior.get('prueba') and time.time() - anterior.get('generado', 0) < VENCE:
        return None  # hay un partido de muestra (?probar_envivo=1): se deja hasta que venza
    copia.escribir(CACHE, datos)
    nueva = huella(datos)
    return nueva if nueva != huella(anterior) else None


def estado(texto):
    """El estado de ESPN en castellano: "HT" → Entretiempo, "5:32 - 2nd" → 2.º cuarto 5:32."""
    texto = (texto or '').strip()
    if texto.upper() in ('HT', 'HALFTIME', 'HALF'):
        return 'Entretiempo'
    m = re.match(r"(\d+:\d+)\s*-\s*(\d)(?:st|nd|rd|th)$", texto)
    if m:
        return f'{m.group(2)}.º cuarto {m.group(1)}'
    m = re.match(r'End of (\d)(?:st|nd|rd|th)', texto)
    if m:
        return f'Fin del {m.group(1)}.º cuarto'
    if texto.upper() in ('OT', 'ET'):
        return 'Alargue'
    return texto


def items():
    """ListItems de la fila (se llama desde default.py)."""
    import xbmcgui
    from resources.lib import copia, guia
    datos = copia.leer(CACHE)
    if datos is None:  # primera vez (o se borró el perfil): directo del homelab
        actualizar()
        datos = copia.leer(CACHE) or {}
    if time.time() - datos.get('generado', 0) > VENCE:
        return []
    salida = []
    for p in datos.get('partidos', []):
        canales = p.get('canales') or []
        if not canales or len(p.get('equipos', [])) != 2:
            continue
        # el canal que DGO abre directo, si hay; si no, el primero (DGO abre TV en vivo)
        canal = next((c for c in canales if guia.destino_dgo(c['nombre'])), canales[0])
        local, visita = p['equipos']
        titulo = f"{local['nombre']} {local['goles']} - {visita['goles']} {visita['nombre']}"
        cuando = estado(p.get('estado'))
        li = xbmcgui.ListItem(titulo, offscreen=True)
        li.setLabel2(f"{cuando} · {canal['nombre']}")
        li.setArt({'local': local.get('logo', ''), 'visitante': visita.get('logo', ''), 'icon': canal.get('logo', ''),
                   'thumb': canal.get('logo', ''), 'logo': canal.get('logo', '')})
        otros = [c['nombre'] for c in canales if c is not canal]
        tag = li.getVideoInfoTag()
        tag.setMediaType('video')
        tag.setTitle(titulo)
        tag.setPlot(f"{local['completo']} vs. {visita['completo']}."
                    + (f" También en {', '.join(otros)}." if otros else ''))
        li.setProperty('vidrio.tipo', 'partido')
        li.setProperty('vidrio.vivo', '1')
        li.setProperty('vidrio.pastilla', 'EN VIVO')
        li.setProperty('vidrio.marcador', f"{local['goles']} - {visita['goles']}")
        li.setProperty('vidrio.etiqueta', f"EN VIVO  ·  {p['competencia']}")
        li.setProperty('vidrio.meta', f"{cuando}  ·  {canal['nombre']}")
        li.setProperty('vidrio.estado', cuando)
        li.setProperty('vidrio.canal', canal['nombre'])
        li.setProperty('vidrio.competencia', p['competencia'])
        li.setProperty('vidrio.goles_local', str(local['goles']))
        li.setProperty('vidrio.goles_visita', str(visita['goles']))
        li.setProperty('vidrio.dgo', guia.destino_dgo(canal['nombre']))
        salida.append((canal['id'], li))
    return salida


DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def cuando(inicio, ahora=None):
    """"Hoy 21:00", "Mañana 15:00", "Domingo 29 17:00" (hora de este equipo)."""
    ahora = ahora or time.time()
    hoy, dia = time.localtime(ahora), time.localtime(inicio)
    hora = time.strftime('%H:%M', dia)
    dias = (time.mktime((dia.tm_year, dia.tm_mon, dia.tm_mday, 0, 0, 0, 0, 0, -1))
            - time.mktime((hoy.tm_year, hoy.tm_mon, hoy.tm_mday, 0, 0, 0, 0, 0, -1))) / 86400
    if round(dias) == 0:
        return 'Hoy', hora
    if round(dias) == 1:
        return 'Mañana', hora
    return f'{DIAS[dia.tm_wday]} {dia.tm_mday}', hora


def proximos():
    """ListItems de "Próximos partidos": los que empiezan en los próximos 7 días, con canal si la guía ya lo tiene."""
    import xbmcgui
    from resources.lib import copia, guia
    datos = copia.leer(CACHE) or {}
    if time.time() - datos.get('generado', 0) > VENCE:
        return []
    ahora, salida = time.time(), []
    for p in datos.get('proximos', []):
        if p.get('inicio', 0) < ahora - 600 or len(p.get('equipos', [])) != 2:
            continue
        canales = p.get('canales') or []
        canal = next((c for c in canales if guia.destino_dgo(c['nombre'])), canales[0] if canales else None)
        local, visita = p['equipos']
        dia, hora = cuando(p['inicio'], ahora)
        donde = canal['nombre'] if canal else 'Canal a confirmar'
        titulo = f"{local['nombre']} vs. {visita['nombre']}"
        li = xbmcgui.ListItem(titulo, offscreen=True)
        li.setLabel2(f'{dia} {hora} · {donde}')
        li.setArt({'local': local.get('logo', ''), 'visitante': visita.get('logo', ''),
                   'logo': canal.get('logo', '') if canal else '', 'icon': 'DefaultVideo.png'})
        tag = li.getVideoInfoTag()
        tag.setMediaType('video')
        tag.setTitle(titulo)
        otros = [c['nombre'] for c in canales if c is not canal]
        tag.setPlot(f"{local['completo']} vs. {visita['completo']}."
                    + (f" También en {', '.join(otros)}." if otros else '')
                    + ('' if canal else ' La guía todavía no llega a ese día: el canal aparece uno o dos días antes.'))
        li.setProperty('vidrio.tipo', 'partido')
        li.setProperty('vidrio.vivo', '0')
        li.setProperty('vidrio.pastilla', dia.upper())
        li.setProperty('vidrio.marcador', 'vs')
        li.setProperty('vidrio.estado', hora)
        li.setProperty('vidrio.etiqueta', f"PRÓXIMO  ·  {p['competencia']}")
        li.setProperty('vidrio.meta', f'{dia} {hora}  ·  {donde}')
        li.setProperty('vidrio.competencia', p['competencia'])
        li.setProperty('vidrio.aviso', f'{dia} {hora} · {donde}')
        li.setProperty('vidrio.dgo', guia.destino_dgo(canal['nombre']) if canal else '')
        salida.append((p['id'], li))
    return salida


def prueba(activar=True):
    """Diagnóstico (?probar_envivo=1): un partido de muestra en la copia local para ver la fila sin esperar uno de
    verdad. Dura hasta que el servicio baje partidos.json del homelab o 10 minutos; ?probar_envivo=0 lo borra."""
    from resources.lib import copia
    import xbmcgui
    if activar:
        espn, dtv = 'https://a.espncdn.com/i/teamlogos/soccer/500/', 'https://dnqt2wx2urq99.cloudfront.net/ondirectv/LOGOS/Canales/AR/'
        datos = {'generado': int(time.time()), 'prueba': True, 'partidos': [{
            'id': 'prueba', 'competencia': 'Primera División', 'inicio': int(time.time()) - 2100,
            'estado': "35'", 'reloj': "35'",
            'equipos': [{'nombre': 'Boca', 'completo': 'Boca Juniors', 'logo': espn + '5.png', 'goles': '1'},
                        {'nombre': 'Ind. Rivadavia', 'completo': 'Independiente Rivadavia', 'logo': espn + '9744.png',
                         'goles': '0'}],
            'canales': [{'id': 'ESPN PREMIUM.ar', 'nombre': 'ESPN Premium', 'logo': dtv + '1604.png', 'dgo': True},
                        {'id': 'FOX SPORTS ARGENTINA.ar', 'nombre': 'Fox Sports', 'logo': dtv + '1605.png',
                         'dgo': True}]}]}
    else:
        datos = {'generado': int(time.time()), 'partidos': []}
    datos['proximos'] = (copia.leer(CACHE) or {}).get('proximos', [])
    copia.escribir(CACHE, datos)
    xbmcgui.Window(10000).setProperty('Vidrio.EnVivo', huella(datos) + str(int(time.time())))
    return len(datos['partidos'])
