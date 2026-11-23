#!/usr/bin/env python3
"""Arma el catálogo que usa el add-on Vidrio en Kodi, sin biblioteca de Kodi.

Textos en español (sinopsis, géneros, episodios) salen de Jellyfin (es-419); tráileres, duración e idioma original de
Radarr/Sonarr, con Jellyfin de respaldo. Escribe /srv/kodi-addons/vidrio/catalogo.json (Samba KodiAddons).

Título: el original si la película o serie es de habla inglesa o española; si no, el título en español (queda también
en 'titulo_es' para buscar). Sinopsis: en español; si Jellyfin la tiene en inglés o vacía, se pide en español a Seerr
(TMDb, es-MX y después es-ES) y, si TMDb no la tiene, se toma de sinopsis_es.json (traducciones propias).
Uso: sudo catalogo.py [--salida RUTA]
"""
import json, os, re, shutil, sqlite3, sys, tempfile, time, urllib.request

JF_DB = '/mnt/media/docker/jellyfin/data/data/jellyfin.db'
# Jellyfin sirve las imágenes achicadas sin sesión; el Apple TV las pide directo (puerto publicado del contenedor)
HOMELAB = os.environ.get('VIDRIO_HOMELAB', '192.168.1.50')  # IP del homelab vista desde el Apple TV
JF_IMAGEN = f'http://{HOMELAB}:8097/Items/{{id}}/Images/Primary?fillWidth=640&quality=80'
SALIDA = sys.argv[sys.argv.index('--salida') + 1] if '--salida' in sys.argv else '/srv/kodi-addons/vidrio/catalogo.json'
RAIZ = {'/movies/': ('/mnt/media/peliculas/', f'smb://{HOMELAB}/Peliculas/'),
        '/tv/': ('/mnt/media/series/', f'smb://{HOMELAB}/Series/')}
SEERR = '/mnt/media/docker/seerr/settings.json'  # Seerr consulta TMDb: sinopsis en español que Jellyfin no tiene
CORRECCIONES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sinopsis_es.json')
IDIOMAS_ORIGINAL = {'English', 'Spanish'}  # títulos que se muestran en su idioma original
VIDEO = re.compile(r'\.(mkv|mp4|m4v|avi|mov|ts|m2ts|wmv)$', re.I)
YT = re.compile(r'(?:v=|youtu\.be/|/embed/)([\w-]{11})')


def arr(app, port, ep):
    key = re.search(r'<ApiKey>(\w+)</ApiKey>', open(f'/mnt/media/docker/{app}/config.xml').read()).group(1)
    req = urllib.request.Request(f'http://127.0.0.1:{port}/api/v3/{ep}', headers={'X-Api-Key': key})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except Exception as e:  # el catálogo sale igual, sin tráileres de esa app
        print(f'aviso: {app} no respondió ({e})', file=sys.stderr)
        return []


def smb(path):
    for jf, (host, url) in RAIZ.items():
        if path and path.startswith(jf):
            return url + path[len(jf):], host + path[len(jf):]
    return None, None


def carpeta(path, nivel):
    """Nombre de la carpeta de la película/serie (nivel 1 = primera carpeta bajo la raíz)."""
    for jf in RAIZ:
        if path and path.startswith(jf):
            return path[len(jf):].split('/')[nivel - 1]
    return None


GENEROS = {'Action & Adventure': ['Acción', 'Aventura'], 'Sci-Fi & Fantasy': ['Ciencia ficción', 'Fantasía'],
           'War & Politics': ['Bélica', 'Política'], 'Suspense': ['Suspenso'], 'Kids': ['Infantil'],
           'News': ['Noticias'], 'Soap': ['Telenovela'], 'Talk': ['Entrevistas']}


GENEROS_EN = {'Action': 'Acción', 'Adventure': 'Aventura', 'Animation': 'Animación', 'Comedy': 'Comedia',
              'Crime': 'Crimen', 'Documentary': 'Documental', 'Drama': 'Drama', 'Family': 'Familia', 'Fantasy': 'Fantasía',
              'History': 'Historia', 'Horror': 'Terror', 'Music': 'Música', 'Mystery': 'Misterio', 'Romance': 'Romance',
              'Science Fiction': 'Ciencia ficción', 'Thriller': 'Suspenso', 'War': 'Bélica', 'Western': 'Western',
              'TV Movie': 'Película de TV'}
ARCHIVO = re.compile(r'S\d{1,2}E\d{1,3}|\b(2160p|1080p|720p|480p|remux|bluray|web-?dl)\b|\.(mkv|mp4)$', re.I)
SXE = re.compile(r'S\d{1,2}E\d{1,3}', re.I)
BASURA = re.compile(r'\(?\b(2160p|1080p|720p|480p|4k|uhd|hdr\d*\+?|dv|remux|bluray|web-?dl|webrip|hevc|x26[45]|h\.?26[45])\b\)?', re.I)


def parece_archivo(texto):
    """True si el título es un nombre de archivo (Jellyfin no identificó el video)."""
    return not texto or bool(ARCHIVO.search(texto))


def titulo_episodio(texto, numero):
    """Título legible para un episodio que Jellyfin dejó con el nombre del archivo."""
    if not parece_archivo(texto):
        return texto
    resto = SXE.split(texto, 1)[1] if SXE.search(texto) else ''
    resto = re.sub(r'\.(mkv|mp4|m4v|avi|ts)$', '', resto, flags=re.I)
    resto = BASURA.sub('', resto).replace('.', ' ').strip(' -_()[]')
    resto = re.sub(r'\s{2,}', ' ', resto)
    return resto if len(resto) > 2 else f'Episodio {numero}'


GENERICO = re.compile(r'^(episodio|episode|cap[ií]tulo)\s*\d+$', re.I)


def episodios_sonarr(serie):
    """{(temporada, episodio): título original} de Sonarr, para episodios sin título en español."""
    if not serie.get('id'):
        return {}
    titulos = {}
    for e in arr('sonarr', 8989, f"episode?seriesId={serie['id']}"):
        t = (e.get('title') or '').strip()
        if t and t != 'TBA' and not GENERICO.match(t):
            titulos[(e.get('seasonNumber'), e.get('episodeNumber'))] = t
    return titulos


def lista(valor):
    return [g for g in (valor or '').split('|') if g]


def generos(valor):
    """Géneros de Jellyfin en castellano: traduce los combinados de TMDb para series y quita repetidos."""
    out = []
    for g in lista(valor):
        for t in GENEROS.get(g, [g]):
            if t not in out:
                out.append(t)
    return out


def minutos(ticks):
    return round(ticks / 600000000) if ticks else 0


def trailer_jf(data):
    try:
        for t in json.loads(data or '{}').get('RemoteTrailers') or []:
            m = YT.search(t.get('Url', ''))
            if m:
                return m.group(1)
    except ValueError:
        pass
    return ''


def anio(valor, fecha):
    return valor or (int(fecha[:4]) if fecha and fecha[:4].isdigit() else 0)


PALABRAS_EN = re.compile(r'\b(the|and|with|his|her|their|when|after|who|is|of|to|a|an|in|on)\b', re.I)
PALABRAS_ES = re.compile(r'\b(el|la|los|las|que|una|un|del|con|por|para|su|sus|es|en|y)\b', re.I)
ANIO_FINAL = re.compile(r'\s*\(\d{4}\)$')


def en_ingles(texto):
    """True si la sinopsis está en inglés (cuenta palabras frecuentes de cada idioma)."""
    return len(PALABRAS_EN.findall(texto or '')) > len(PALABRAS_ES.findall(texto or ''))


def limpiar_titulo(t):
    return ANIO_FINAL.sub('', (t or '').strip())


_seerr = {}


def sinopsis_seerr(tipo, tmdb):
    """Sinopsis en español de TMDb a través de Seerr ('movie' o 'tv'), o '' si no hay."""
    return datos_seerr(tipo, tmdb).get('sinopsis', '')


def datos_seerr(tipo, tmdb):
    """{'titulo', 'sinopsis'} en español de TMDb a través de Seerr ('movie' o 'tv'); {} si no hay."""
    if not tmdb:
        return {}
    if 'clave' not in _seerr:
        try:
            _seerr['clave'] = json.load(open(SEERR))['main']['apiKey']
        except (OSError, ValueError, KeyError):
            _seerr['clave'] = None
    if not _seerr['clave']:
        return {}
    if (tipo, tmdb) in _seerr:
        return _seerr[(tipo, tmdb)]
    datos = {}
    for idioma in ('es-MX', 'es-ES'):
        req = urllib.request.Request(f'http://127.0.0.1:5055/api/v1/{tipo}/{tmdb}?language={idioma}',
                                     headers={'X-Api-Key': _seerr['clave']})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:
            print(f'aviso: Seerr no respondió para {tipo} {tmdb} ({e})', file=sys.stderr)
            break
        datos.setdefault('titulo', (r.get('title') or r.get('name') or '').strip())
        texto = (r.get('overview') or '').strip()
        if texto and not en_ingles(texto):
            datos['sinopsis'] = texto
            break
    _seerr[(tipo, tmdb)] = datos
    return datos


def corregir(x, tipo, idioma, original, correcciones):
    """Aplica la regla de título y la sinopsis en español a una película ('movie') o serie ('tv')."""
    x['titulo_es'] = limpiar_titulo(x['titulo'])
    x['titulo'] = limpiar_titulo(original) if idioma in IDIOMAS_ORIGINAL and original else x['titulo_es']
    x['original'] = limpiar_titulo(original or x.get('original'))
    x['idioma'] = idioma or ''
    if not x['sinopsis'] or en_ingles(x['sinopsis']):
        tmdb = x.get('ids', {}).get('tmdb')
        nueva = (sinopsis_seerr(tipo, tmdb) or correcciones.get(f'{tipo}:{tmdb}', '')
                 or correcciones.get(f"{tipo}:carpeta:{x.get('carpeta')}", ''))  # sin código de TMDb: por carpeta
        if nueva:
            x['sinopsis'] = nueva
        elif x['sinopsis']:
            print(f'aviso: sin sinopsis en español para {x["titulo"]} ({tipo} {tmdb}): agregarla a sinopsis_es.json',
                  file=sys.stderr)


def main():
    tmp = tempfile.mkdtemp()
    try:
        db = os.path.join(tmp, 'jf.db')
        shutil.copyfile(JF_DB, db)  # copia: no tocar la base mientras Jellyfin la usa
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        filas = con.execute(
            "select Id, Type, Name, OriginalTitle, ProductionYear, PremiereDate, Overview, Genres, RunTimeTicks, "
            "CommunityRating, OfficialRating, Tagline, Path, Data, SeriesId, ParentIndexNumber, IndexNumber, Studios "
            "from BaseItems where Type in ('MediaBrowser.Controller.Entities.Movies.Movie',"
            "'MediaBrowser.Controller.Entities.TV.Series','MediaBrowser.Controller.Entities.TV.Episode') "
            "and IsVirtualItem = 0").fetchall()
        con_imagen = {r[0] for r in con.execute("select distinct ItemId from BaseItemImageInfos where ImageType = 0")}
        proveedores = {}
        for item, prov, valor in con.execute("select ItemId, ProviderId, ProviderValue from BaseItemProviders"):
            proveedores.setdefault(item, {})[prov.lower()] = valor
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    radarr = {os.path.basename(m['path'].rstrip('/')): m for m in arr('radarr', 7878, 'movie') if m.get('path')}
    sonarr = {os.path.basename(s['path'].rstrip('/')): s for s in arr('sonarr', 8989, 'series') if s.get('path')}

    peliculas, series, episodios = [], {}, {}
    for f in filas:
        tipo = f['Type'].rsplit('.', 1)[-1]
        url, local = smb(f['Path'])
        if not url:
            continue
        base = {
            'titulo': f['Name'] or '', 'original': f['OriginalTitle'] or '', 'anio': anio(f['ProductionYear'], f['PremiereDate']),
            'sinopsis': f['Overview'] or '', 'generos': generos(f['Genres']), 'minutos': minutos(f['RunTimeTicks']),
            'puntaje': round(f['CommunityRating'], 1) if f['CommunityRating'] else 0, 'clasificacion': f['OfficialRating'] or '',
            'lema': f['Tagline'] or '', 'estudios': lista(f['Studios']), 'agregada': 0,
        }
        if tipo == 'Movie':
            nombre = carpeta(f['Path'], 1)
            r = radarr.get(nombre, {})
            dir_local = os.path.dirname(local)
            if not os.path.isfile(local):
                continue
            if r and (parece_archivo(base['titulo']) or not base['sinopsis']):
                # Jellyfin no la identificó: datos de Radarr (también en español)
                base.update(titulo=r.get('title') or base['titulo'], original=r.get('originalTitle') or '',
                            anio=r.get('year') or base['anio'], sinopsis=base['sinopsis'] or r.get('overview') or '',
                            generos=base['generos'] or [GENEROS_EN.get(g, g) for g in r.get('genres', [])],
                            clasificacion=base['clasificacion'] or r.get('certification') or '')
            jf = proveedores.get(f['Id'], {})
            if r.get('tmdbId') and (str(r['tmdbId']) != (jf.get('tmdb') or str(r['tmdbId'])) or BASURA.search(base['titulo'])
                                    or '#' in base['titulo']):
                # Jellyfin la identificó mal (otra película) o dejó el nombre del archivo: vale lo de Radarr
                es = datos_seerr('movie', str(r['tmdbId']))
                base.update(titulo=es.get('titulo') or r.get('title') or base['titulo'], original=r.get('originalTitle') or '',
                            anio=r.get('year') or base['anio'], sinopsis=es.get('sinopsis') or r.get('overview') or '',
                            generos=[GENEROS_EN.get(g, g) for g in r.get('genres', [])] or base['generos'],
                            clasificacion=r.get('certification') or '', lema='')
                print(f"aviso: {nombre}: Jellyfin la tiene como otra película o sin identificar; uso Radarr ({base['titulo']})",
                      file=sys.stderr)
            base['ids'] = {k: v for k, v in {'tmdb': str(r.get('tmdbId') or jf.get('tmdb') or ''),
                                              'imdb': r.get('imdbId') or jf.get('imdb') or ''}.items() if v and v != '0'}
            base.update(carpeta=nombre, archivo=url, dir=url.rsplit('/', 1)[0] + '/',
                        trailer=r.get('youTubeTrailerId') or trailer_jf(f['Data']),
                        minutos=base['minutos'] or r.get('runtime') or 0,
                        agregada=int(os.path.getmtime(dir_local)))
            peliculas.append(base)
        elif tipo == 'Series':
            nombre = carpeta(f['Path'], 1)
            s = sonarr.get(nombre, {})
            jf = proveedores.get(f['Id'], {})
            base['ids'] = {k: v for k, v in {'tvdb': str(s.get('tvdbId') or jf.get('tvdb') or ''),
                                              'tmdb': str(s.get('tmdbId') or jf.get('tmdb') or ''),
                                              'imdb': s.get('imdbId') or jf.get('imdb') or ''}.items() if v and v != '0'}
            base.update(carpeta=nombre, dir=url.rstrip('/') + '/', trailer=trailer_jf(f['Data']),
                        minutos=base['minutos'] or s.get('runtime') or 0, cadena=s.get('network') or '',
                        estado='En emisión' if s.get('status') == 'continuing' else ('Finalizada' if s else ''),
                        agregada=int(os.path.getmtime(local)) if os.path.isdir(local) else 0, temporadas=[])
            series[f['Id']] = base
        elif tipo == 'Episode' and f['SeriesId'] and VIDEO.search(f['Path'] or '') and os.path.isfile(local):
            episodios.setdefault(f['SeriesId'], []).append({
                'titulo': titulo_episodio(base['titulo'], f['IndexNumber'] or 0), 'sinopsis': base['sinopsis'],
                'minutos': base['minutos'],
                'temporada': f['ParentIndexNumber'] or 0, 'episodio': f['IndexNumber'] or 0, 'archivo': url,
                'estreno': (f['PremiereDate'] or '')[:10], 'agregada': int(os.path.getmtime(local)),
                'imagen': JF_IMAGEN.format(id=f['Id'].replace('-', '').lower()) if f['Id'] in con_imagen else '',
            })

    try:
        correcciones = json.load(open(CORRECCIONES, encoding='utf-8'))
    except (OSError, ValueError):
        correcciones = {}
    for p in peliculas:
        r = radarr.get(p['carpeta'], {})
        corregir(p, 'movie', (r.get('originalLanguage') or {}).get('name'), r.get('originalTitle') or p['original'], correcciones)
    for s in series.values():
        so = sonarr.get(s['carpeta'], {})
        idioma = (so.get('originalLanguage') or {}).get('name')
        original = s['original'] or (so.get('title') if idioma == 'English' else '')
        corregir(s, 'tv', idioma, original, correcciones)

    for sid, s in series.items():
        eps = sorted(episodios.get(sid, []), key=lambda e: (e['temporada'], e['episodio']))
        if any(GENERICO.match(e['titulo'].strip()) for e in eps):
            # TMDb no tiene el título en español (Jellyfin deja "Episodio N"): usar el título original de Sonarr
            originales = episodios_sonarr(sonarr.get(s['carpeta'], {}))
            for e in eps:
                if GENERICO.match(e['titulo'].strip()) and (e['temporada'], e['episodio']) in originales:
                    e['titulo'] = originales[(e['temporada'], e['episodio'])]
        temporadas = {}
        for e in eps:
            temporadas.setdefault(e['temporada'], []).append(e)
        s['temporadas'] = [{'numero': n, 'episodios': v} for n, v in sorted(temporadas.items())]
        if eps:
            s['agregada'] = max(s['agregada'], max(e['agregada'] for e in eps))

    catalogo = {'version': 1, 'generado': int(time.time()),
                'peliculas': sorted(peliculas, key=lambda p: p['titulo'].lower()),
                'series': sorted(series.values(), key=lambda s: s['titulo'].lower())}
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    parcial = SALIDA + '.tmp'
    with open(parcial, 'w', encoding='utf-8') as fh:
        json.dump(catalogo, fh, ensure_ascii=False, separators=(',', ':'))
    os.chmod(parcial, 0o644)
    os.replace(parcial, SALIDA)
    neps = sum(len(t['episodios']) for s in series.values() for t in s['temporadas'])
    print(f'catálogo: {len(peliculas)} películas ({sum(1 for p in peliculas if p["trailer"])} con tráiler), '
          f'{len(series)} series ({sum(1 for s in series.values() if s["trailer"])} con tráiler), {neps} episodios')


if __name__ == '__main__':
    main()
