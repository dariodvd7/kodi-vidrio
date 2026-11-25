# -*- coding: utf-8 -*-
"""Catálogo sin homelab: arma catalogo.json leyendo carpetas de películas y series (locales, smb://, nfs://...).

Para quien no tiene Jellyfin, Radarr y Sonarr. Ajustes: "Origen del catálogo" = Carpetas, la carpeta de películas y
la de series. Se esperan los nombres de siempre:
  Películas/<Título (Año)>/<video>                      (o el video suelto: Películas/<Título (Año)>.mkv)
  Series/<Título (Año)>/Season 1/<... S01E02 ...>.mkv    (o Temporada 1, S01, o los episodios sin subcarpeta)
Datos de cada título, en este orden:
  1. TMDb, si hay clave (ajuste "Clave de TMDb", gratis en themoviedb.org: la "API Key" o el "API Read Access
     Token"): título, sinopsis, géneros, puntaje, duración, tráiler, imágenes y episodios en español. Se guarda en el
     perfil (tmdb.json) para no volver a pedirlo.
  2. Un .nfo de Kodi al lado (movie.nfo, <video>.nfo, tvshow.nfo).
  3. El nombre de la carpeta.
Imágenes: folder.jpg/poster.jpg y fanart.jpg de la carpeta; si no hay, las de TMDb.
El servicio lo vuelve a armar cada 12 horas; el botón "Actualizar el catálogo ahora" de los ajustes, al momento.
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon('plugin.video.vidrio')
PERFIL = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
CATALOGO = os.path.join(PERFIL, 'catalogo_carpetas.json')
TMDB_CACHE = os.path.join(PERFIL, 'tmdb.json')
VIGENCIA = 12 * 3600
TMDB = 'https://api.themoviedb.org/3/'
IMAGEN = 'https://image.tmdb.org/t/p/'
VIDEO = re.compile(r'\.(mkv|mp4|m4v|avi|mov|ts|m2ts|wmv|mpg|mpeg|webm)$', re.I)
DESCARTAR = re.compile(r'(^|[ ._-])(sample|trailer|featurette|extras?)([ ._-]|$)', re.I)
EPISODIO = re.compile(r'[Ss](\d{1,2})[ ._-]?[Ee](\d{1,3})|(?<!\d)(\d{1,2})x(\d{2,3})(?!\d)')
SOLO_EPISODIO = re.compile(r'(?:^|[ ._-])(?:e|ep|episodio|episode|cap[ií]tulo|capitulo)[ ._-]?(\d{1,3})(?!\d)', re.I)
# Lo que viene después del número de episodio hasta la calidad: "S01E02.La.Caida.1080p" -> "La Caida"
CALIDAD = re.compile(r'(?:^|[ ._-])(?:\d{3,4}p|web|webrip|web-dl|bluray|bdrip|hdtv|dvdrip|x26[45]|h[ .]?26[45]|hevc|amzn|nf|dsnp|hmax|atvp?|pcok|ddp?5|aac|repack|proper|multi|dual|doc|french|german|spanish|latino|castellano|subbed|internal|imax|hdr|dv|10bit)(?:[ ._-]|$)|[(\[]', re.I)
TEMPORADA = re.compile(r'^(?:season|temporada|serie|s)[ ._-]*(\d{1,2})$', re.I)
CON_ANIO = re.compile(r'^(.*?)[ ._(\[-]+((?:19|20)\d{2})[)\]]?(?:[ ._-].*)?$')
IDIOMAS_ORIGINAL = {'en', 'es'}  # como el catálogo del homelab: estos títulos se muestran en su idioma original
# Géneros de TMDb por número, con los nombres que usan las filas de la skin (Acción, Suspenso...)
GENEROS = {28: ['Acción'], 12: ['Aventura'], 16: ['Animación'], 35: ['Comedia'], 80: ['Crimen'], 99: ['Documental'],
           18: ['Drama'], 10751: ['Familia'], 14: ['Fantasía'], 36: ['Historia'], 27: ['Terror'], 10402: ['Música'],
           9648: ['Misterio'], 10749: ['Romance'], 878: ['Ciencia ficción'], 10770: ['Película de TV'],
           53: ['Suspenso'], 10752: ['Bélica'], 37: ['Western'], 10759: ['Acción', 'Aventura'], 10762: ['Infantil'],
           10763: ['Noticias'], 10764: ['Reality'], 10765: ['Ciencia ficción', 'Fantasía'], 10766: ['Telenovela'],
           10767: ['Entrevistas'], 10768: ['Bélica', 'Política']}


def log(msg, nivel=xbmc.LOGINFO):
    xbmc.log(f'[vidrio] carpetas: {msg}', nivel)


def activo():
    return ADDON.getSettingString('fuente') == 'carpetas'


def releer():
    """El servicio vive mucho: después de un cambio en los ajustes, volver a leerlos."""
    global ADDON
    ADDON = xbmcaddon.Addon('plugin.video.vidrio')


def ajustes():
    """Lo que define el catálogo: si cambia (otra carpeta, la clave de TMDb), hay que rearmarlo ya."""
    return [ADDON.getSettingString(k).strip() for k in ('carpeta_peliculas', 'carpeta_series')] + \
        [bool(ADDON.getSettingString('tmdb_clave').strip())]


def hace_falta():
    try:
        if time.time() - os.path.getmtime(CATALOGO) > VIGENCIA:
            return True
    except OSError:
        return True
    return (leer() or {}).get('ajustes') != ajustes()


def leer():
    from resources.lib import copia
    return copia.leer(CATALOGO)


# --- carpetas -----------------------------------------------------------------------------------------------------

def barra(ruta):
    return ruta if ruta.endswith('/') or ruta.endswith('\\') else ruta + '/'


def listar(ruta):
    try:
        dirs, archivos = xbmcvfs.listdir(barra(ruta))
        return sorted(d for d in dirs if not d.startswith('.')), sorted(a for a in archivos if not a.startswith('.'))
    except Exception as e:
        log(f'no puedo leer {ruta}: {e}', xbmc.LOGWARNING)
        return [], []


def modificado(ruta):
    try:
        st = xbmcvfs.Stat(ruta)
        return int(st.st_mtime()), int(st.st_size())
    except Exception:
        return 0, 0


def nombre_y_anio(texto):
    """"Nueve reinas (2000)" o "Nueve.Reinas.2000.1080p" -> ("Nueve reinas", 2000)."""
    texto = VIDEO.sub('', texto)
    m = CON_ANIO.match(texto)
    nombre, anio = (m.group(1), int(m.group(2))) if m else (texto, None)
    if not nombre.strip():  # "2001 (2001)": el año era el nombre
        nombre, anio = texto, None
    nombre = re.sub(r'[._]+', ' ', nombre)
    return re.sub(r'\s+', ' ', nombre).strip(' -'), anio


def imagenes(dir_, archivos):
    nombres = {a.lower(): a for a in archivos}
    poster = next((nombres[n] for n in ('folder.jpg', 'poster.jpg', 'folder.png', 'poster.png') if n in nombres), None)
    fondo = next((nombres[n] for n in ('fanart.jpg', 'backdrop.jpg', 'fanart.png', 'background.jpg') if n in nombres), None)
    return (dir_ + poster if poster else None), (dir_ + fondo if fondo else None)


def leer_nfo(ruta):
    """Datos de un .nfo de Kodi (película o serie), o {} si no hay o no se entiende."""
    try:
        with xbmcvfs.File(ruta) as fh:
            texto = fh.read()
        raiz = ET.fromstring(texto[texto.index('<'):])
    except Exception:
        return {}

    def t(tag):
        el = raiz.find(tag)
        return (el.text or '').strip() if el is not None and el.text else ''
    d = {'titulo': t('title'), 'original': t('originaltitle'), 'sinopsis': t('plot') or t('outline'),
         'lema': t('tagline'), 'clasificacion': t('mpaa'),
         'generos': [g.text.strip() for g in raiz.findall('genre') if g.text],
         'estudios': [g.text.strip() for g in raiz.findall('studio') if g.text][:3]}
    if t('year').isdigit():
        d['anio'] = int(t('year'))
    if t('runtime').isdigit():
        d['minutos'] = int(t('runtime'))
    try:
        d['puntaje'] = round(float(t('rating') or raiz.find('ratings/rating/value').text), 1)
    except Exception:
        pass
    ids = {u.get('type'): u.text.strip() for u in raiz.findall('uniqueid') if u.get('type') and u.text}
    if t('tmdbid'):
        ids.setdefault('tmdb', t('tmdbid'))
    if t('imdbid') or (t('id').startswith('tt')):
        ids.setdefault('imdb', t('imdbid') or t('id'))
    d['ids'] = {k: v for k, v in ids.items() if k in ('tmdb', 'imdb', 'tvdb')}
    m = re.search(r'(?:v=|video_id=|youtu\.be/|/embed/)([\w-]{11})', t('trailer'))
    if m:
        d['trailer'] = m.group(1)
    return {k: v for k, v in d.items() if v}


# --- TMDb ---------------------------------------------------------------------------------------------------------

class Tmdb:
    def __init__(self, clave):
        self.clave = clave.strip()
        from resources.lib import copia
        self.cache = copia.leer(TMDB_CACHE) or {}
        self.fallas = 0

    def __bool__(self):
        return bool(self.clave)

    def pedir(self, ruta, **q):
        if self.fallas >= 5:  # clave mala o sin internet: no insistir con cada título
            return None
        cabeceras = {'Accept': 'application/json'}
        if len(self.clave) > 40:  # "API Read Access Token" (v4): va en la cabecera
            cabeceras['Authorization'] = f'Bearer {self.clave}'
        else:
            q['api_key'] = self.clave
        url = TMDB + ruta + '?' + urllib.parse.urlencode(q)
        for intento in range(3):  # un corte de conexión o un 429 (demasiados pedidos): esperar y reintentar
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=cabeceras), timeout=20) as r:
                    return json.load(r)
            except Exception as e:
                codigo = getattr(e, 'code', None)
                if intento < 2 and (codigo in (429, 500, 502, 503, 504) or codigo is None):
                    time.sleep(2 * (intento + 1))
                    continue
                self.fallas += 1
                log(f'TMDb {ruta}: {codigo or ""} {e}', xbmc.LOGWARNING)
                return None

    def guardar(self):
        from resources.lib import copia
        copia.escribir(TMDB_CACHE, self.cache)

    def buscar(self, tipo, nombre, anio):
        """Número de TMDb del título ("movie" o "tv"): el resultado más parecido en título y año. Primero con el año;
        sin el año solo uno muy parecido (si no, "The Order" terminaba en "Harry Potter y la Orden del Fénix"). Si no
        hay nada, de nuevo sin lo que esté entre paréntesis ("The Pitt (Latino)")."""
        clave = f'v4:{tipo}:{nombre.lower()}:{anio or ""}'
        if clave in self.cache:
            return self.cache[clave]
        campo = 'primary_release_year' if tipo == 'movie' else 'first_air_date_year'
        nombres = [nombre]
        limpio = re.sub(r'\s*[(\[][^)\]]*[)\]]\s*', ' ', nombre).strip()
        if limpio and limpio != nombre:
            nombres.append(limpio)
        elegido = None
        for n in nombres:
            for con_anio in ([True] if anio else []) + [False]:
                # títulos en inglés para comparar: los nombres de carpeta suelen estar en inglés (Radarr, Sonarr) o
                # en el idioma original ("Hope" coreana es "Hope: El primer impacto" en es-MX); los datos, en español
                r = self.pedir(f'search/{tipo}', query=n, language='en-US', **({campo: anio} if con_anio else {}))
                # sin año en la carpeta no hay con qué exigir: vale el más parecido
                elegido = mejor(n, anio, (r or {}).get('results', []), exigente=bool(anio) and not con_anio)
                if elegido:
                    break
            if elegido:
                break
        if elegido or self.fallas < 5:  # sin conexión no se anota "no está"
            self.cache[clave] = elegido
        return elegido

    def ficha(self, tipo, numero):
        clave = f'{tipo}/{numero}'
        if clave in self.cache:
            return self.cache[clave]
        extra = 'videos,external_ids' + (',release_dates' if tipo == 'movie' else ',content_ratings')
        d = self.pedir(f'{tipo}/{numero}', language='es-MX', append_to_response=extra,
                       include_video_language='es,en')
        if d and not d.get('overview'):  # sin sinopsis en México: la de España
            es = self.pedir(f'{tipo}/{numero}', language='es-ES')
            if es and es.get('overview'):
                d['overview'] = es['overview']
        if d:
            self.cache[clave] = d
        return d

    def temporada(self, numero, temporada):
        """Episodios de una temporada. TMDb pone "Episodio N" cuando no hay título en español: esos quedan vacíos
        (el armado usa el del archivo) y se guarda aparte el título en inglés como último recurso."""
        clave = f'v2:tv/{numero}/season/{temporada}'
        if clave not in self.cache:
            d = self.pedir(f'tv/{numero}/season/{temporada}', language='es-MX')
            if not d:
                return {}
            eps = {str(e['episode_number']): {
                'titulo': '' if GENERICO.match(e.get('name') or '') else (e.get('name') or ''),
                'sinopsis': e.get('overview') or '', 'estreno': e.get('air_date') or '', 'minutos': e.get('runtime') or 0,
                'imagen': IMAGEN + 'w780' + e['still_path'] if e.get('still_path') else ''} for e in d.get('episodes', [])}
            if any(not e['titulo'] for e in eps.values()):
                en = self.pedir(f'tv/{numero}/season/{temporada}', language='en-US') or {}
                for e in en.get('episodes', []):
                    x = eps.get(str(e['episode_number']))
                    if x is not None and not GENERICO.match(e.get('name') or ''):
                        x['titulo_en'] = e.get('name') or ''
            self.cache[clave] = eps
        return self.cache[clave]


GENERICO = re.compile(r'^(episodio|episode|cap[ií]tulo)\s*\d+$', re.I)


def _parecido(a, b):
    from difflib import SequenceMatcher
    a, b = (re.sub(r'[^a-z0-9 ]', '', (x or '').lower()) for x in (a, b))
    return SequenceMatcher(None, a, b).ratio() if a and b else 0


def mejor(nombre, anio, resultados, exigente=False):
    """El resultado de TMDb más parecido. Suma: parecido del título (traducido u original), el año (si la carpeta lo
    tiene), el orden de TMDb (que ya ordena por relevancia) y que el nombre de la carpeta esté entero en el título
    ("The Hunt" en "The Hunt: Prey vs Predator"). Exigente (la búsqueda con año no dio nada y se probó sin año): solo
    un título casi igual o de un año vecino."""
    elegido, puntos_max = None, 0
    buscado = f" {re.sub(r'[^a-z0-9]+', ' ', nombre.lower()).strip()} "
    for orden, r in enumerate(resultados[:10]):
        titulos = [r.get('title'), r.get('original_title'), r.get('name'), r.get('original_name')]
        parecido = max(_parecido(nombre, t) for t in titulos)
        entero = any(buscado in f" {re.sub(r'[^a-z0-9]+', ' ', (t or '').lower()).strip()} " for t in titulos)
        fecha = (r.get('release_date') or r.get('first_air_date') or '')[:4]
        dif = abs(int(fecha) - anio) if anio and fecha.isdigit() else None
        if exigente and parecido < 0.85 and dif not in (0, 1):
            continue
        puntos = (parecido + (0.5 if dif == 0 else 0.25 if dif == 1 else 0) + max(0, 0.3 - 0.1 * orden)
                  + (0.2 if entero else 0) + 0.3 * min(1, (r.get('vote_count') or 0) / 50))  # conocido > desconocido
        if puntos > puntos_max:
            elegido, puntos_max = r['id'], puntos
    return elegido if puntos_max >= 0.5 else None


def datos_tmdb(d, tipo):
    """Ficha de TMDb -> campos del catálogo."""
    original = d.get('original_title') or d.get('original_name') or ''
    titulo_es = d.get('title') or d.get('name') or original
    salida = {
        'titulo': original if d.get('original_language') in IDIOMAS_ORIGINAL and original else titulo_es,
        'titulo_es': titulo_es, 'original': original, 'sinopsis': d.get('overview') or '',
        'lema': d.get('tagline') or '', 'idioma': d.get('original_language') or '',
        'generos': list(dict.fromkeys(g for x in d.get('genres', []) for g in GENEROS.get(x['id'], [x['name']]))),
        'puntaje': round(d['vote_average'], 1) if d.get('vote_average') else None,
        'estudios': [c['name'] for c in (d.get('production_companies') or d.get('networks') or [])][:3],
        'ids': {k: str(v) for k, v in (('tmdb', d.get('id')), ('imdb', (d.get('external_ids') or {}).get('imdb_id')),
                                       ('tvdb', (d.get('external_ids') or {}).get('tvdb_id'))) if v},
    }
    fecha = d.get('release_date') or d.get('first_air_date') or ''
    if fecha[:4].isdigit():
        salida['anio'] = int(fecha[:4])
    minutos = d.get('runtime') or (d.get('episode_run_time') or [0])[0]
    if minutos:
        salida['minutos'] = minutos
    videos = [v for v in (d.get('videos') or {}).get('results', []) if v.get('site') == 'YouTube']
    videos.sort(key=lambda v: (v.get('type') != 'Trailer', v.get('iso_639_1') != 'es', not v.get('official')))
    if videos:
        salida['trailer'] = videos[0]['key']
    if tipo == 'tv':
        salida['estado'] = 'Finalizada' if d.get('status') in ('Ended', 'Canceled') else 'En emisión'
    if d.get('poster_path'):
        salida['poster'] = IMAGEN + 'w500' + d['poster_path']
    if d.get('backdrop_path'):
        salida['fanart'] = IMAGEN + 'w1280' + d['backdrop_path']
    return {k: v for k, v in salida.items() if v not in (None, '', [], {})}


# --- armado -------------------------------------------------------------------------------------------------------

def pelicula(base, nombre, tmdb):
    """Una película: carpeta propia o video suelto en la carpeta de películas."""
    if VIDEO.search(nombre):  # video suelto
        dir_, archivos, videos = base, [], [nombre]
        titulo, anio = nombre_y_anio(nombre)
    else:
        dir_ = barra(base + nombre)
        _, archivos = listar(dir_)
        videos = [a for a in archivos if VIDEO.search(a) and not DESCARTAR.search(a)]
        titulo, anio = nombre_y_anio(nombre)
    if not videos:
        return None
    medidas = {v: modificado(dir_ + v) for v in videos}
    video = max(videos, key=lambda v: medidas[v][1])  # el más grande: no el sample
    p = {'titulo': titulo, 'carpeta': nombre, 'dir': dir_, 'archivo': dir_ + video,
         'agregada': medidas[video][0] or int(time.time())}
    if anio:
        p['anio'] = anio
    base_video = video.rsplit('.', 1)[0]
    for nfo in ('movie.nfo', base_video + '.nfo'):
        if nfo in archivos:
            p.update(leer_nfo(dir_ + nfo))
            break
    if tmdb:
        numero = (p.get('ids') or {}).get('tmdb') or tmdb.buscar('movie', titulo, anio)
        ficha = tmdb.ficha('movie', numero) if numero else None
        if ficha:
            p.update(datos_tmdb(ficha, 'movie'))
    poster, fondo = imagenes(dir_, archivos)
    if poster:
        p['poster'] = poster
    if fondo:
        p['fanart'] = fondo
    return p


def titulo_de_archivo(resto):
    """El título del episodio en el nombre del archivo, si hay: lo de después del número, hasta la calidad."""
    resto = VIDEO.sub('', resto)
    m = CALIDAD.search(resto)
    resto = resto[:m.start()] if m else resto
    resto = re.sub(r'[._]+', ' ', resto).strip(' -')
    return resto if len(resto) > 1 and not resto.isdigit() else ''


def episodios_de(dir_serie, dirs, archivos):
    """[(temporada, episodio, ruta, título del archivo)] de una serie, en subcarpetas de temporada o sueltos."""
    encontrados = []

    def sumar(dir_, nombres, temporada_carpeta):
        for a in nombres:
            if not VIDEO.search(a) or DESCARTAR.search(a):
                continue
            m = EPISODIO.search(a)
            solo = SOLO_EPISODIO.search(a)
            if m:
                t, e = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), int(m.group(4)))
                resto = a[m.end():]
            elif solo:  # "E01 Los cinco mandamientos.mp4": sin temporada, la de la carpeta o la 1
                t, e, resto = (1 if temporada_carpeta is None else temporada_carpeta), int(solo.group(1)), a[solo.end():]
            elif temporada_carpeta is not None:
                n = re.search(r'(?<!\d)(\d{1,3})(?!\d)', a)
                if not n:
                    continue
                t, e, resto = temporada_carpeta, int(n.group(1)), a[n.end():]
            else:
                continue
            encontrados.append((t, e, dir_ + a, titulo_de_archivo(resto)))
    sumar(dir_serie, archivos, None)
    for d in dirs:
        m = TEMPORADA.match(d.strip())
        especiales = d.lower() in ('specials', 'especiales', 'season 0', 'temporada 0')
        if m or especiales:
            sub = barra(dir_serie + d)
            _, nombres = listar(sub)
            sumar(sub, nombres, 0 if especiales else int(m.group(1)))
    unicos = {}  # dos archivos del mismo episodio (otra calidad): uno solo
    for x in sorted(set(encontrados)):
        unicos.setdefault(x[:2], x)
    return list(unicos.values())


def serie(base, nombre, tmdb):
    dir_ = barra(base + nombre)
    dirs, archivos = listar(dir_)
    eps = episodios_de(dir_, dirs, archivos)
    if not eps:
        return None
    titulo, anio = nombre_y_anio(nombre)
    s = {'titulo': titulo, 'carpeta': nombre, 'dir': dir_}
    if anio:
        s['anio'] = anio
    if 'tvshow.nfo' in archivos:
        s.update(leer_nfo(dir_ + 'tvshow.nfo'))
    numero = ficha = None
    if tmdb:
        numero = (s.get('ids') or {}).get('tmdb') or tmdb.buscar('tv', titulo, anio)
        ficha = tmdb.ficha('tv', numero) if numero else None
        if ficha:
            s.update(datos_tmdb(ficha, 'tv'))
    poster, fondo = imagenes(dir_, archivos)
    if poster:
        s['poster'] = poster
    if fondo:
        s['fanart'] = fondo
    temporadas = {}
    for t, e, ruta, de_archivo in eps:
        info = (tmdb.temporada(numero, t) if ficha else {}).get(str(e), {})
        agregada, _ = modificado(ruta)
        ep = {'temporada': t, 'episodio': e, 'archivo': ruta, 'titulo': info.get('titulo') or de_archivo or info.get('titulo_en') or f'Episodio {e}',
              'sinopsis': info.get('sinopsis', ''), 'estreno': info.get('estreno', ''),
              'minutos': info.get('minutos') or s.get('minutos') or 0, 'imagen': info.get('imagen', ''),
              'agregada': agregada or int(time.time())}
        temporadas.setdefault(t, []).append(ep)
    s['temporadas'] = [{'numero': t, 'episodios': temporadas[t]} for t in sorted(temporadas, key=lambda n: (n == 0, n))]
    s['agregada'] = max(e['agregada'] for t in s['temporadas'] for e in t['episodios'])
    return s


def escanear(progreso=None):
    """Arma el catálogo de las carpetas de los ajustes y lo guarda. Devuelve (películas, series)."""
    from resources.lib import copia
    tmdb = Tmdb(ADDON.getSettingString('tmdb_clave'))
    trabajos = []
    for ajuste, tipo in (('carpeta_peliculas', 'pelicula'), ('carpeta_series', 'serie')):
        base = ADDON.getSettingString(ajuste).strip()
        if base:
            base = barra(base)
            dirs, archivos = listar(base)
            nombres = dirs + ([a for a in archivos if VIDEO.search(a)] if tipo == 'pelicula' else [])
            trabajos += [(tipo, base, n) for n in nombres]
    peliculas, series = [], []
    for i, (tipo, base, nombre) in enumerate(trabajos):
        if progreso:
            progreso(int(100 * i / max(1, len(trabajos))), nombre)
        try:
            if tipo == 'pelicula':
                x = pelicula(base, nombre, tmdb)
                if x:
                    peliculas.append(x)
            else:
                x = serie(base, nombre, tmdb)
                if x:
                    series.append(x)
        except Exception as e:  # un título raro no frena el resto
            log(f'{nombre}: {type(e).__name__}: {e}', xbmc.LOGWARNING)
        if tmdb and i % 25 == 24:
            tmdb.guardar()
    if tmdb:
        tmdb.guardar()
    catalogo = {'version': 1, 'generado': int(time.time()), 'origen': 'carpetas', 'ajustes': ajustes(),
                'peliculas': sorted(peliculas, key=lambda x: x['titulo'].lower()),
                'series': sorted(series, key=lambda x: x['titulo'].lower())}
    copia.escribir(CATALOGO, catalogo)
    log(f'{len(peliculas)} películas y {len(series)} series'
        + (f' (TMDb falló {tmdb.fallas} veces)' if tmdb and tmdb.fallas else '') + ('' if tmdb else ' (sin TMDb)'))
    return len(peliculas), len(series)
