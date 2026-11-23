# -*- coding: utf-8 -*-
"""Listados de Vidrio: películas, series, temporadas y episodios con datos completos.

Rutas (plugin://plugin.video.vidrio/?...):
  lista=peliculas|series|recientes|generos   genero=<nombre>[&tipo=peliculas|series]
  serie=<carpeta>[&temporada=<n>]            buscar=1 (pide texto)   refrescar=1
  limite=<n> recorta cualquier lista (para filas del inicio).
"""
import sys
from urllib.parse import parse_qsl, quote, quote_plus, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from resources.lib.catalogo import cargar

BASE, HANDLE = sys.argv[0], int(sys.argv[1])
P = dict(parse_qsl(sys.argv[2][1:]))
YOUTUBE = 'plugin://plugin.video.youtube/play/?video_id={}'


def url(**q):
    return f'{BASE}?{urlencode(q)}'


def arte(item, dir_):
    poster, fanart = dir_ + 'folder.jpg', dir_ + 'fanart.jpg'
    return {'poster': poster, 'fanart': fanart, 'thumb': fanart, 'landscape': fanart, 'icon': poster}


def comun(li, d, tipo):
    tag = li.getVideoInfoTag()
    tag.setMediaType(tipo)
    tag.setTitle(d.get('titulo', ''))
    if d.get('original') and d['original'] != d.get('titulo'):
        tag.setOriginalTitle(d['original'])
    if d.get('anio'):
        tag.setYear(int(d['anio']))
    tag.setPlot(d.get('sinopsis', ''))
    tag.setGenres(d.get('generos', []))
    if d.get('minutos'):
        tag.setDuration(int(d['minutos']) * 60)
    if d.get('puntaje'):
        tag.setRating(float(d['puntaje']))
    if d.get('clasificacion'):
        tag.setMpaa(d['clasificacion'])
    if d.get('lema'):
        tag.setTagLine(d['lema'])
    if d.get('estudios'):
        tag.setStudios(d['estudios'])
    if d.get('trailer'):
        tag.setTrailer(YOUTUBE.format(d['trailer']))
    if d.get('ids'):
        tag.setUniqueIDs(d['ids'], 'tvdb' if tipo == 'tvshow' and 'tvdb' in d['ids'] else ('tmdb' if 'tmdb' in d['ids'] else next(iter(d['ids']))))
    # Propiedades propias para la skin (texto ya armado en español)
    generos = ', '.join(d.get('generos', [])[:2])
    li.setProperty('vidrio.generos', generos)
    li.setProperty('vidrio.duracion', duracion(d.get('minutos', 0)))
    li.setProperty('vidrio.trailer', YOUTUBE.format(d['trailer']) if d.get('trailer') else '')
    return tag


def normalizar(texto):
    """Minúsculas y sin acentos, para buscar 'accion' y encontrar 'Acción'."""
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', texto or '').lower() if unicodedata.category(c) != 'Mn')


def duracion(m):
    if not m:
        return ''
    h, m = divmod(int(m), 60)
    return f'{h} h {m} min' if h and m else (f'{h} h' if h else f'{m} min')


def item_pelicula(p):
    li = xbmcgui.ListItem(p['titulo'], offscreen=True)
    comun(li, p, 'movie')
    li.setArt(arte(p, p['dir']))
    li.setProperty('vidrio.tipo', 'pelicula')
    li.setProperty('vidrio.etiqueta', 'PELÍCULA')
    li.setProperty('vidrio.meta', ' · '.join(x for x in (str(p.get('anio') or ''), li.getProperty('vidrio.generos'),
                                                         li.getProperty('vidrio.duracion'), p.get('clasificacion', '')) if x))
    li.setProperty('IsPlayable', 'true')
    # Se reproduce a través del add-on: si la ruta fuera el archivo de Samba, Kodi buscaría los datos en el scraper de
    # esa carpeta (en inglés) en lugar de usar los del catálogo.
    return url(reproducir=p['archivo']), li, False


def item_serie(s):
    li = xbmcgui.ListItem(s['titulo'], offscreen=True)
    tag = comun(li, s, 'tvshow')
    tag.setTvShowTitle(s['titulo'])
    temporadas = len(s.get('temporadas', []))
    li.setArt(arte(s, s['dir']))
    li.setProperty('vidrio.tipo', 'serie')
    li.setProperty('vidrio.etiqueta', 'SERIE')
    tt = f'{temporadas} temporada' + ('s' if temporadas != 1 else '') if temporadas else ''
    li.setProperty('vidrio.meta', ' · '.join(x for x in (str(s.get('anio') or ''), li.getProperty('vidrio.generos'),
                                                         tt, s.get('cadena', '')) if x))
    li.setProperty('TotalSeasons', str(temporadas))
    li.setProperty('vidrio.carpeta_q', quote_plus(s['carpeta']))
    # Abre la pantalla de serie de la skin Vidrio (ventana 1150) desde cualquier lista
    return url(abrir_serie=s['carpeta']), li, True


def item_episodio(s, e):
    li = xbmcgui.ListItem(e['titulo'], offscreen=True)
    tag = comun(li, {**e, 'generos': s.get('generos', [])}, 'episode')
    tag.setTvShowTitle(s['titulo'])
    tag.setSeason(int(e.get('temporada') or 0))
    tag.setEpisode(int(e.get('episodio') or 0))
    if e.get('estreno'):
        tag.setFirstAired(e['estreno'])
    li.setArt({**arte(s, s['dir']), 'thumb': e.get('imagen') or s['dir'] + 'fanart.jpg'})
    li.setProperty('vidrio.tipo', 'episodio')
    li.setProperty('vidrio.numero', f"EPISODIO {e['episodio']}" if e.get('episodio') else 'ESPECIAL')
    # Título para la tarjeta: vacío si solo repite el número ("Episodio 3"), que ya está arriba
    repetido = e['titulo'].strip().lower() == f"episodio {e.get('episodio')}"
    li.setProperty('vidrio.titulo', '' if repetido else e['titulo'])
    li.setProperty('vidrio.meta', ' · '.join(x for x in (f"T{e.get('temporada')} E{e.get('episodio')}",
                                                         duracion(e.get('minutos')), e.get('estreno', '')) if x))
    li.setProperty('IsPlayable', 'true')
    return url(reproducir=e['archivo']), li, False


def mismo(ids_trakt, ids_catalogo):
    """True si algún código (tmdb, imdb, tvdb) de Trakt coincide con el del catálogo."""
    ids_catalogo = ids_catalogo or {}
    return any(str(ids_trakt.get(k) or '') and str(ids_trakt.get(k)) == str(ids_catalogo.get(k) or '')
               for k in ('tmdb', 'imdb', 'tvdb'))


def continuar(pelis, series):
    """Lo que hay para seguir viendo según Trakt, lo más reciente primero: películas y episodios a medias (se retoman
    desde donde quedaron) y, de las series que venís viendo, el episodio que sigue al último que terminaste."""
    from resources.lib import trakt
    items = []  # (fecha, item)
    en_curso = set()
    for r in trakt.reproducciones():
        progreso = float(r.get('progress') or 0)
        if r.get('type') == 'movie':
            p = next((p for p in pelis if mismo(r['movie'].get('ids', {}), p.get('ids'))), None)
            if not p:
                continue
            u, li, carpeta = item_pelicula(p)
            minutos = p.get('minutos')
            archivo = p['archivo']
        elif r.get('type') == 'episode':
            t, n = r['episode'].get('season'), r['episode'].get('number')
            s = next((s for s in series if mismo(r['show'].get('ids', {}), s.get('ids'))), None)
            e = s and next((e for tt in s['temporadas'] for e in tt['episodios']
                            if str(e.get('temporada')) == str(t) and str(e.get('episodio')) == str(n)), None)
            if not e:
                continue
            u, li, carpeta = item_episodio(s, e)
            li.setLabel(f"{s['titulo']} · T{t} E{n}")
            li.setArt(arte(s, s['dir']))  # la tarjeta de la fila usa el fondo de la serie
            minutos = e.get('minutos') or s.get('minutos')
            archivo = e['archivo']
        else:
            continue
        total = int(minutos or 0) * 60
        if total:
            li.getVideoInfoTag().setResumePoint(total * progreso / 100, total)
            quedan = round(total * (100 - progreso) / 100 / 60)
            li.setProperty('vidrio.meta', f"Te quedan {duracion(quedan) or '1 min'}  ·  {li.getProperty('vidrio.meta')}")
        li.setProperty('vidrio.etiqueta', 'CONTINUAR VIENDO')
        li.setProperty('vidrio.continuar', '1')
        li.setProperty('vidrio.progreso', str(int(progreso)))
        if r.get('type') == 'episode':
            en_curso.add(s['carpeta'])
        items.append((r.get('paused_at', ''), (url(reproducir=archivo, desde=f'{progreso:.2f}'), li, carpeta)))

    # Siguiente episodio: por cada serie del historial (la más reciente primero), el que sigue al último que viste
    vistas = set()
    for h in trakt.historial():
        s = next((s for s in series if mismo(h.get('show', {}).get('ids', {}), s.get('ids'))), None)
        if not s or s['carpeta'] in vistas:
            continue
        vistas.add(s['carpeta'])
        if s['carpeta'] in en_curso or len(vistas) > 15:
            continue
        t, n = h.get('episode', {}).get('season'), h.get('episode', {}).get('number')
        eps = [e for tt in s['temporadas'] for e in tt['episodios'] if (e.get('temporada') or 0) > 0]
        eps.sort(key=lambda e: (int(e.get('temporada') or 0), int(e.get('episodio') or 0)))
        proximo = next((e for e in eps if (int(e.get('temporada') or 0), int(e.get('episodio') or 0)) > (int(t or 0), int(n or 0))), None)
        if not proximo:
            continue
        u, li, carpeta = item_episodio(s, proximo)
        li.setLabel(f"{s['titulo']} · T{proximo['temporada']} E{proximo['episodio']}")
        li.setArt(arte(s, s['dir']))
        li.setProperty('vidrio.etiqueta', 'SIGUIENTE EPISODIO')
        li.setProperty('vidrio.continuar', '1')
        li.setProperty('vidrio.meta', f"Siguiente episodio  ·  {li.getProperty('vidrio.meta')}")
        items.append((h.get('watched_at', ''), (url(reproducir=proximo['archivo']), li, carpeta)))
    items.sort(key=lambda x: x[0], reverse=True)
    return [i for _, i in items]


def mi_lista(pelis, series, ya):
    """La lista de seguimiento de Trakt (watchlist) con lo que está en el catálogo."""
    from resources.lib import trakt
    items = []
    for r in trakt.lista():
        if r.get('type') == 'movie':
            p = next((p for p in pelis if mismo(r['movie'].get('ids', {}), p.get('ids'))), None)
            item = p and item_pelicula(p)
        else:
            s = next((s for s in series if mismo(r['show'].get('ids', {}), s.get('ids'))), None)
            item = s and item_serie(s)
        if item and item[0] not in ya:
            item[1].setProperty('vidrio.etiqueta', 'MI LISTA')
            items.append(item)
    return items


MIS_CANALES = 'Mis canales'


def editar_mis_canales():
    """Botón "Mis canales" de la guía: marcar y desmarcar canales. Los elegidos quedan primero, en su orden."""
    import time
    from resources.lib import guia
    g = guia.cargar()
    canales = g.get('canales', [])
    actuales = guia.mis_canales(g)
    por_id = {i: c for c in canales for i in [c['id']] + c.get('otros_ids', [])}  # otros_ids: canales unidos
    elegidos = [por_id[i] for i in actuales if i in por_id]
    solo_dgo = xbmcaddon.Addon().getSettingBool('solo_dgo')
    elegidos = list({id(c): c for c in elegidos}.values())  # dos ids que hoy son el mismo canal: una vez
    orden = elegidos + [c for c in canales if c not in elegidos and not (solo_dgo and c.get('dgo') is False)]
    opciones = []
    for c in orden:
        li = xbmcgui.ListItem(c['nombre'], c.get('grupo', ''))
        if c.get('logo'):
            li.setArt({'icon': c['logo'], 'thumb': c['logo']})
        opciones.append(li)
    sel = xbmcgui.Dialog().multiselect('Mis canales', opciones, preselect=list(range(len(elegidos))), useDetails=True)
    if sel is None:  # canceló
        return
    guia.guardar_mis_canales([orden[i]['id'] for i in sel])
    # la skin pone esta propiedad en la dirección de la fila: al cambiar, Kodi la vuelve a cargar
    xbmcgui.Window(10000).setProperty('Vidrio.MisCanales', str(int(time.time())))


def canales_guia(grupo):
    """Canales de un grupo de la guía de TV con lo que dan ahora (para la ventana Guía de la skin)."""
    import time
    from resources.lib import guia
    g = guia.cargar()
    ahora = time.time()
    items = []
    canales = g.get('canales', [])
    if grupo == MIS_CANALES:
        por_id = {i: c for c in canales for i in [c['id']] + c.get('otros_ids', [])}  # otros_ids: canales unidos
        canales = list({id(por_id[i]): por_id[i] for i in guia.mis_canales(g) if i in por_id}.values())
    solo_dgo = xbmcaddon.Addon().getSettingBool('solo_dgo')
    for c in canales:
        if grupo and grupo != MIS_CANALES and c.get('grupo') != grupo:
            continue
        # Los que DGO no tiene ("dgo": false, lo marca homelab/guia.py) no se ven; en "Mis canales" queda lo elegido
        if solo_dgo and grupo != MIS_CANALES and c.get('dgo') is False:
            continue
        actual, siguiente = guia.ahora_y_despues(c, ahora)
        li = xbmcgui.ListItem(c['nombre'], offscreen=True)
        tag = li.getVideoInfoTag()
        tag.setMediaType('video')
        if c.get('logo'):
            li.setArt({'icon': c['logo'], 'thumb': c['logo'], 'logo': c['logo']})
        li.setProperty('vidrio.tipo', 'canal')
        li.setProperty('vidrio.canal_id', c['id'])
        li.setProperty('vidrio.grupo', c.get('grupo', ''))
        li.setProperty('vidrio.dgo', guia.destino_dgo(c['nombre']))
        if actual:
            total, pasado = actual['fin'] - actual['inicio'], ahora - actual['inicio']
            tag.setTitle(actual['titulo'])
            tag.setPlot(actual.get('sinopsis', ''))
            tag.setResumePoint(pasado, total)  # barra de progreso del programa (ListItem.PercentPlayed)
            li.setProperty('vidrio.ahora', actual['titulo'])
            li.setProperty('vidrio.horario', f"{guia.hora(actual['inicio'])} – {guia.hora(actual['fin'])}")
            quedan = max(1, round((actual['fin'] - ahora) / 60))
            li.setProperty('vidrio.quedan', f'Quedan {duracion(quedan)}')
        else:
            li.setProperty('vidrio.ahora', 'Sin programación')
        if siguiente:
            li.setProperty('vidrio.siguiente', f"{guia.hora(siguiente['inicio'])}  {siguiente['titulo']}")
        items.append((url(canal=c['id']), li, False))
    return items


def terminar(items, contenido, orden=True):
    limite = int(P.get('limite', 0) or 0)
    if limite:
        items = items[:limite]
    xbmcplugin.addDirectoryItems(HANDLE, items, len(items))
    xbmcplugin.setContent(HANDLE, contenido)
    if orden:
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def raiz():
    entradas = [('Películas', url(lista='peliculas'), 'DefaultMovies.png'),
                ('Series', url(lista='series'), 'DefaultTVShows.png'),
                ('Agregadas recientemente', url(lista='recientes'), 'DefaultRecentlyAddedMovies.png'),
                ('Géneros', url(lista='generos'), 'DefaultGenre.png'),
                ('Buscar', url(buscar=1), 'DefaultAddonsSearch.png')]
    items = []
    for nombre, u, icono in entradas:
        li = xbmcgui.ListItem(nombre, offscreen=True)
        li.setArt({'icon': icono, 'thumb': icono})
        items.append((u, li, True))
    terminar(items, 'videos', orden=False)


def main():
    if P.get('editar_mis_canales'):
        editar_mis_canales()
        if HANDLE >= 0:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)
        return
    if P.get('abrir'):  # abrir otra app por su enlace (tvOS: DGO desde la guía); ver resources/lib/abrir.py
        # Lo hace el servicio, que sigue vivo cuando tvOS avisa el resultado (este proceso termina enseguida y tvOS
        # llamaría a una función que ya no existe: Kodi se cierra).
        xbmcgui.Window(10000).setProperty('Vidrio.Abrir', P['abrir'])
        if HANDLE >= 0:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)
        return
    cat = cargar(forzar=P.get('refrescar') == '1')
    pelis, series = cat.get('peliculas', []), cat.get('series', [])
    if 'reproducir' in P:
        # El ítem que se reproduce lleva todos los datos (título, año, temporada/episodio): los usa la barra de
        # reproducción y a4kSubtitles para buscar los subtítulos.
        archivo = P['reproducir']
        li = next((item_pelicula(p)[1] for p in pelis if p['archivo'] == archivo), None)
        if li is None:
            li = next((item_episodio(s, e)[1] for s in series for t in s['temporadas'] for e in t['episodios']
                       if e['archivo'] == archivo), None)
        li = li or xbmcgui.ListItem(offscreen=True)
        li.setPath(archivo)
        if P.get('desde'):  # desde "Continuar viendo": retomar donde quedó según Trakt
            li.setProperty('StartPercent', P['desde'])
        # Trakt (script.trakt) identifica lo que no está en la biblioteca con esta propiedad: códigos de la película o,
        # para un episodio, los de la serie (temporada y episodio los toma del reproductor).
        ids = next((p.get('ids') for p in pelis if p['archivo'] == archivo), None)
        if ids is None:
            ids = next((s.get('ids') for s in series for t in s['temporadas'] for e in t['episodios']
                        if e['archivo'] == archivo), None)
        if ids:
            import json
            xbmcgui.Window(10000).setProperty('script.trakt.ids', json.dumps(ids))
        else:
            xbmcgui.Window(10000).clearProperty('script.trakt.ids')
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
        return
    lista = P.get('lista')

    if 'abrir_serie' in P:
        xbmcgui.Window(10000).setProperty('Vidrio.SerieQ', quote_plus(P['abrir_serie']))
        # Un segundo después, cuando la lista ya terminó de procesar el clic: así Atrás vuelve a esa lista.
        xbmc.executebuiltin('AlarmClock(vidrioserie,ActivateWindow(1150),00:01,silent)')
        return xbmcplugin.endOfDirectory(HANDLE, succeeded=False, updateListing=False, cacheToDisc=False)

    if 'serie' in P:
        s = next((x for x in series if x['carpeta'] == P['serie']), None)
        if not s:
            return terminar([], 'tvshows')
        if 'info' in P:  # la serie misma, para el encabezado de la pantalla de serie
            return terminar([item_serie(s)], 'tvshows', orden=False)
        if 'temporada' in P:
            t = next((t for t in s['temporadas'] if str(t['numero']) == P['temporada']), {'episodios': []})
            return terminar([item_episodio(s, e) for e in t['episodios']], 'episodes', orden=False)
        if len(s['temporadas']) == 1 and 'temporadas' not in P:  # una sola temporada: directo a los episodios
            return terminar([item_episodio(s, e) for e in s['temporadas'][0]['episodios']], 'episodes', orden=False)
        items = []
        for t in s['temporadas']:
            nombre = 'Especiales' if t['numero'] == 0 else f"Temporada {t['numero']}"
            u, li, _ = item_serie(s)
            li.setLabel(nombre)
            li.getVideoInfoTag().setMediaType('season')
            li.getVideoInfoTag().setSeason(int(t['numero']))
            li.setProperty('vidrio.meta', f"{len(t['episodios'])} episodios")
            li.setProperty('vidrio.temporada', str(t['numero']))
            items.append((url(serie=s['carpeta'], temporada=t['numero']), li, True))
        return terminar(items, 'seasons', orden=False)

    orden = P.get('orden', '')
    claves = {'anio': lambda x: -(x.get('anio') or 0), 'reciente': lambda x: -(x.get('agregada') or 0),
              'puntaje': lambda x: -(x.get('puntaje') or 0)}
    if orden in claves:
        pelis, series = sorted(pelis, key=claves[orden]), sorted(series, key=claves[orden])
    if lista == 'peliculas':
        return terminar([item_pelicula(p) for p in pelis], 'movies', orden=not orden)
    if lista == 'series':
        return terminar([item_serie(s) for s in series], 'tvshows', orden=not orden)
    if lista == 'recientes':
        todo = [(p['agregada'], item_pelicula(p)) for p in pelis] + [(s['agregada'], item_serie(s)) for s in series]
        return terminar([i for _, i in sorted(todo, key=lambda x: -x[0])], 'movies', orden=False)
    if lista == 'guia':  # ventana Guía de la skin: una fila por grupo
        return terminar(canales_guia(P.get('grupo', '')), 'videos', orden=False)
    if 'canal' in P:  # elegir un canal desde una lista común: la skin lo maneja; acá no hay nada que reproducir
        return xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)
    if lista in ('continuar', 'trakt'):
        items = continuar(pelis, series)
        if lista == 'trakt':
            items += mi_lista(pelis, series, {i[0] for i in items})
        return terminar(items, 'movies', orden=False)
    if lista == 'generos':
        todos = pelis + series
        generos = sorted({g for x in todos for g in x.get('generos', [])}, key=normalizar)
        # fondo de cada tarjeta: el título mejor puntuado del género que no haya usado otro género (los más grandes eligen primero)
        usados, destacados = set(), {}
        for g in sorted(generos, key=lambda g: -sum(1 for x in todos if g in x.get('generos', []))):
            candidatos = sorted((x for x in todos if g in x.get('generos', [])), key=lambda x: -(x.get('puntaje') or 0))
            elegido = next((x for x in candidatos if x['dir'] not in usados), candidatos[0])
            usados.add(elegido['dir'])
            destacados[g] = elegido
        items = []
        for g in generos:
            del_genero = [x for x in todos if g in x.get('generos', [])]
            destacado = destacados[g]
            li = xbmcgui.ListItem(g, offscreen=True)
            li.setLabel2(f"{len(del_genero)} títulos")
            fanart = destacado['dir'] + 'fanart.jpg'
            li.setArt({'icon': 'DefaultGenre.png', 'thumb': fanart, 'fanart': fanart})
            li.setProperty('vidrio.genero_q', quote_plus(g))
            li.setProperty('vidrio.cantidad', str(len(del_genero)))
            items.append((url(genero=g), li, True))
        if P.get('ventana') == '1':  # la pantalla de géneros de la skin: los que más títulos tienen primero
            items.sort(key=lambda i: -int(i[1].getProperty('vidrio.cantidad')))
        return terminar(items, 'genres', orden=False)
    if 'genero' in P:
        g = P['genero']
        items = [item_pelicula(p) for p in pelis if g in p.get('generos', [])]  # ya ordenadas según ?orden=
        if P.get('tipo') != 'peliculas':
            items += [item_serie(s) for s in series if g in s.get('generos', [])]
        return terminar(items, 'movies')
    if 'buscar' in P:
        ventana = P.get('ventana') == '1'  # pantalla de búsqueda de la skin: sin diálogo, sugerencias si está vacío
        texto = P.get('texto', '').strip()
        if not texto and not ventana:
            texto = xbmcgui.Dialog().input('Buscar películas y series')
        if not texto:
            if ventana:  # sugerencias: lo agregado últimamente
                todo = [(p['agregada'], item_pelicula(p)) for p in pelis] + [(s['agregada'], item_serie(s)) for s in series]
                return terminar([i for _, i in sorted(todo, key=lambda x: -x[0])][:24], 'movies', orden=False)
            return terminar([], 'movies')
        t = normalizar(texto)
        def puntaje(x):
            # título que se muestra, original y en español: "21 gramos" encuentra "21 Grams"
            campos = [normalizar(x['titulo']), normalizar(x.get('original', '')), normalizar(x.get('titulo_es', ''))]
            if any(c.startswith(t) for c in campos):
                return 0
            if any(f' {t}' in f' {c}' for c in campos):
                return 1
            if any(t in c for c in campos):
                return 2
            if any(normalizar(g).startswith(t) for g in x.get('generos', [])):  # "accion" trae las de acción
                return 3
            return None
        res = [(puntaje(p), p['titulo'], item_pelicula(p)) for p in pelis] + \
              [(puntaje(s), s['titulo'], item_serie(s)) for s in series]
        res = sorted((r for r in res if r[0] is not None), key=lambda r: (r[0], normalizar(r[1])))
        return terminar([r[2] for r in res], 'movies', orden=False)
    if P.get('copiar_log') == '1':  # diagnóstico: copia el log de Kodi a la carpeta indicada (por defecto KodiLogs)
        import xbmcvfs
        import re as _re
        host = _re.match(r'smb://([^/]+)/', xbmcaddon.Addon().getSettingString('catalogo') or '')
        destino = P.get('destino', f"smb://{host.group(1) if host else '192.168.1.50'}/KodiLogs/")
        ok = xbmcvfs.copy('special://logpath/kodi.log', destino + 'kodi.log')
        xbmcgui.Dialog().notification('Vidrio', 'Log copiado' if ok else 'No pude copiar el log', xbmcgui.NOTIFICATION_INFO, 3000)
        return terminar([], 'videos')
    if P.get('log'):  # diagnóstico: devuelve las líneas de un log de Kodi como listado (para leerlo por JSON-RPC)
        import xbmcvfs
        nombre = P['log'] if P['log'] in ('kodi.log', 'kodi.old.log') else 'kodi.log'
        f = xbmcvfs.File('special://logpath/' + nombre)
        lineas = f.read().splitlines()
        f.close()
        cuantas = int(P.get('cuantas', 1500))
        desde = int(P.get('desde', max(0, len(lineas) - cuantas)))
        items = [(f'{BASE}?nada={i}', xbmcgui.ListItem(f'{i}|{l}'), False) for i, l in enumerate(lineas[desde:desde + cuantas], desde)]
        items.insert(0, (f'{BASE}?nada=total', xbmcgui.ListItem(f'TOTAL|{len(lineas)}'), False))
        return terminar(items, 'files', orden=False)
    if P.get('refrescar') == '1':
        xbmcgui.Dialog().notification('Vidrio', 'Catálogo actualizado', xbmcgui.NOTIFICATION_INFO, 3000)
        return terminar([], 'videos')
    raiz()


main()
