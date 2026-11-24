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
VENCE = 10 * 60
RECORDATORIOS = os.path.join(PERFIL, 'recordatorios.json')
ANTES = 5 * 60  # el aviso sale 5 minutos antes del comienzo  # si el homelab dejó de actualizarlo, la fila no muestra partidos viejos


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
    favs = favoritos()
    for p in sorted(datos.get('partidos', []), key=lambda p: not es_favorito(p, favs)):
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
        if es_favorito(p, favs):
            li.setProperty('vidrio.favorito', '1')
            li.setProperty('vidrio.pastilla', '★ EN VIVO')
            li.setProperty('vidrio.etiqueta', f"★ EN VIVO  ·  {p['competencia']}")
        salida.append((canal['id'], li))
    return salida


MAX_PROXIMOS = 20
NFL_POR_DIA = 3


def _norma(texto):
    import unicodedata
    texto = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', texto).split())


def favoritos():
    """Ajuste "Equipos favoritos" (separados por coma), normalizados: ['river plate', 'chiefs']."""
    ajustes = xbmcaddon.Addon('plugin.video.vidrio')  # nuevo cada vez: el servicio vive mucho y el ajuste cambia
    return [f for f in (_norma(x) for x in ajustes.getSettingString('equipos_favoritos').split(',')) if f]


def es_favorito(p, favs=None):
    """Si juega un equipo favorito: el favorito tiene que estar entero, por palabras, en el nombre corto o completo
    ("packers" en "Green Bay Packers", "racing club" en "Racing Club"; "river" no es "Riverside")."""
    favs = favoritos() if favs is None else favs
    for e in p.get('equipos', []):
        for nombre in (e.get('nombre'), e.get('completo')):
            texto = f' {_norma(nombre)} '
            if any(f' {f} ' in texto for f in favs):
                return True
    return False


def elegir(proximos, favs):
    """Los de los favoritos siempre y primero; del resto, de la NFL como mucho NFL_POR_DIA por día; MAX_PROXIMOS en
    total. El homelab manda todos."""
    fav = [p for p in proximos if es_favorito(p, favs)]
    resto, por_dia = [], {}
    for p in proximos:
        if p in fav:
            continue
        if p.get('competencia') == 'NFL':
            dia = time.strftime('%Y%m%d', time.localtime(p['inicio']))
            por_dia[dia] = por_dia.get(dia, 0) + 1
            if por_dia[dia] > NFL_POR_DIA:
                continue
        resto.append(p)
    return (fav + resto)[:max(MAX_PROXIMOS, len(fav))]


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
    favs = favoritos()
    vigentes = [p for p in datos.get('proximos', []) if p.get('inicio', 0) >= ahora - 600 and len(p.get('equipos', [])) == 2]
    avisos = recordatorios(sumar=vigentes)
    for p in elegir(vigentes, favs):
        favorito = es_favorito(p, favs)
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
        li.setProperty('vidrio.partido_id', str(p['id']))
        if str(p['id']) in avisos:
            li.setProperty('vidrio.recordado', '1')
            li.setProperty('vidrio.pastilla', 'AVISO')
            li.setLabel2(f'Te aviso · {dia} {hora} · {donde}')
            li.setProperty('vidrio.meta', f'{dia} {hora}  ·  {donde}  ·  Te aviso 5 minutos antes')
        if favorito:
            li.setProperty('vidrio.favorito', '1')
            li.setProperty('vidrio.pastilla', '★ ' + li.getProperty('vidrio.pastilla'))
            li.setProperty('vidrio.etiqueta', f"★ FAVORITO  ·  {p['competencia']}")
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


# --- recordatorios --------------------------------------------------------------------------------------------------

def _leer_todo():
    from resources.lib import copia
    todos = copia.leer(RECORDATORIOS) or {}
    return todos, set(todos.pop('_no', []))


def _guardar(todos, no):
    from resources.lib import copia
    copia.escribir(RECORDATORIOS, {**todos, '_no': sorted(no)})


def _nuevo(p):
    local, visita = p['equipos']
    return {'inicio': p['inicio'], 'titulo': f"{local['nombre']} vs. {visita['nombre']}",
            'competencia': p.get('competencia', ''), 'avisado': False}


def recordatorios(sumar=None):
    """{id del partido: {inicio, titulo, competencia, avisado}} de este equipo; los de hace más de 3 horas se borran.
    Con `sumar` (próximos partidos) y el ajuste "Avisarme los partidos de mis favoritos", agrega los de los equipos
    favoritos, salvo los que se sacaron a mano (quedan en "_no")."""
    todos, no = _leer_todo()
    cambio = False
    vigentes = {k: v for k, v in todos.items() if v.get('inicio', 0) > time.time() - 3 * 3600}
    cambio |= len(vigentes) != len(todos)
    if sumar and xbmcaddon.Addon('plugin.video.vidrio').getSettingBool('avisar_favoritos'):
        favs = favoritos()
        for p in sumar:
            pid = str(p.get('id'))
            if favs and pid not in vigentes and pid not in no and len(p.get('equipos', [])) == 2 \
                    and p.get('inicio', 0) > time.time() and es_favorito(p, favs):
                vigentes[pid] = {**_nuevo(p), 'automatico': True}
                cambio = True
    if cambio:
        _guardar(vigentes, {n for n in no if n in {str(p.get('id')) for p in (sumar or [])}} if sumar else no)
    return vigentes


def buscar(pid):
    """El partido con ese id en partidos.json (próximo o ya en juego), o None."""
    from resources.lib import copia
    datos = copia.leer(CACHE) or {}
    return next((p for p in datos.get('partidos', []) + datos.get('proximos', []) if str(p.get('id')) == str(pid)), None)


def alternar(pid):
    """Pone o saca el recordatorio de un próximo partido. Devuelve (puesto, texto para avisar)."""
    recordatorios()
    todos, no = _leer_todo()
    pid = str(pid)
    if pid in todos:
        titulo = todos.pop(pid)['titulo']
        no.add(pid)  # si es de un favorito, que no vuelva a ponerse solo
        _guardar(todos, no)
        return False, f'Sin aviso para {titulo}'
    p = buscar(pid)
    if not p or len(p.get('equipos', [])) != 2:
        return False, 'No encontré ese partido'
    todos[pid] = _nuevo(p)
    no.discard(pid)
    _guardar(todos, no)
    dia, hora = cuando(p['inicio'])
    return True, f'Te aviso 5 minutos antes: {dia} {hora}'


def para_avisar(ahora=None):
    """Recordatorios que tocan ahora (de 5 minutos antes hasta 15 después del comienzo), marcados como avisados.
    Cada uno con el canal que tenga partidos.json en este momento (la guía puede haberlo sumado después)."""
    from resources.lib import copia, guia
    ahora = ahora or time.time()
    datos = copia.leer(CACHE) or {}
    todos = recordatorios(sumar=datos.get('proximos', []))
    _, no = _leer_todo()
    salida = []
    for pid, r in todos.items():
        if r.get('avisado') or not (r['inicio'] - ANTES <= ahora < r['inicio'] + 15 * 60):
            continue
        r['avisado'] = True
        p = buscar(pid) or {}
        canales = p.get('canales') or []
        canal = next((c for c in canales if guia.destino_dgo(c['nombre'])), canales[0] if canales else None)
        minutos = max(0, round((r['inicio'] - ahora) / 60))
        salida.append({**r, 'id': pid, 'minutos': minutos, 'canal': canal['nombre'] if canal else '',
                       'dgo': guia.destino_dgo(canal['nombre']) if canal else ''})
    if salida:
        _guardar(todos, no)
    return salida
