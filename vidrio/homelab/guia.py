#!/usr/bin/env python3
"""Arma la guía de TV que muestra la skin Vidrio (pestaña DGO en Android, Guía en el Apple TV).

Programación: XMLTV públicos de open-epg.com para Argentina (argentina1 y argentina3; argentina2 repite los canales).
Los horarios vienen en UTC. Logos: lista pública de canales de DIRECTV Argentina del proyecto iptv-org/epg.
Escribe /srv/kodi-addons/vidrio/guia.json con los canales agrupados y lo que dan desde una hora antes hasta 36 horas
después. Se corre cada 3 horas desde cron.
Uso: guia.py [--salida RUTA]
"""
import gzip
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

FUENTES = ['https://www.open-epg.com/files/argentina1.xml.gz', 'https://www.open-epg.com/files/argentina3.xml.gz']
LOGOS = 'https://raw.githubusercontent.com/iptv-org/epg/master/sites/directv.com.ar/directv.com.ar.channels.xml'
SALIDA = sys.argv[sys.argv.index('--salida') + 1] if '--salida' in sys.argv else '/srv/kodi-addons/vidrio/guia.json'
ANTES, DESPUES = 3600, 36 * 3600
SIGLAS = {'TV', 'TN', 'C5N', 'A24', 'CNN', 'HBO', 'ESPN', 'TNT', 'AXN', 'AMC', 'TBS', 'TCM', 'MTV', 'BBC', 'DW', 'FX',
          'TYC', 'TLC', 'HD', 'E!', 'A&E', 'SBT', 'TVE', 'DHE', 'DXTV', 'LN+', 'CN23', 'KZO', 'NBA', 'VH1', 'H2', 'IP',
          'TV5', 'RT', 'ID', 'NHK', 'DSPORTS', 'ESPN2', 'ESPN3'}
# No son canales de TV (entradas de apps o radio) o son para adultos
OCULTOS = {'canal de test', 'netflix', 'prime video', 'youtube', 'disney+', 'movistar eventos', 'radio nacional', 'usa',
           'playboy', 'sextreme', 'venus', 'penthouse', 'hot', 'private'}
# Primero en su fila (el resto va por orden alfabético)
PRIMERO = ['Telefe', 'El Trece', 'America TV', 'TV Publica', 'El Nueve', 'TN', 'C5N', 'A24', 'LN+', 'La Nacion+',
           'ESPN', 'ESPN Premium', 'TNT Sports', 'TNT Sports Premium', 'TYC Sports', 'Fox Sports', 'HBO', 'TNT',
           'Warner Channel', 'Star Channel']

# Grupo de cada canal por palabras del nombre (el primero que coincide)
GRUPOS = [
    ('Deportes', r'espn|tnt sports|tyc|fox sports|deportv|d ?sports|golf|nba|adrenalina|america sports|garage|dxtv|gol tv|px sports'),
    ('Noticias', r'\btn\b|c5n|a24|cnn|\bln\+|la nacion|ip noticias|cronica|canal 26|26 ?tv|bbc|\bdw\b|telesur|france 24|\bf24\b|cn23|net tv|canal de la ciudad|\brt\b|euronews'),
    ('Infantiles', r'disney( channel| junior| jr)?$|cartoon|nick|discovery kids|paka ?paka|baby ?tv|cartoonito|\bclan\b|tooncast|dreamworks|zoomoo|tateti|plim plim'),
    ('Internacionales', r'antena ?3|\btve\b|\brai\b|telemundo|las estrellas|sbt|tv chile|tv 5|galicia|canal vasco|bolivia|tlnovelas|hola tv|eurochannel'),
    ('Películas y series', r'hbo|cinemax|\bstar\b|\bcine|tnt|warner|axn|sony|universal|amc|\bfx\b|space|tcm|paramount|comedy|\be! |lifetime|studio|golden|tbs|syfy|a&e|europa|atres|series|movies|adult swim|film'),
    ('Documentales', r'discovery|national|nat geo|animal|history|\bh2\b|smithsonian|encuentro|love nature|\bdhe\b|home (&|and) health|\bid\b|investigation|gourmet|food network|\btlc\b|hgtv|travel|viajar|tec ?tv'),
    ('Música', r'musica|mtv|vh1|much|quiero|\bhtv\b|telehit|cm musical|allegro'),
    ('Aire', r'telefe|el trece|el nueve|america|tv publica|television publica|canal \d|bravo|televida|rural|argentinisima|tele ?10|telemax|metro|el seis|magazine|volver'),
]
# Canales del plan de DGO (canales_dgo.json, al lado de este archivo: los nombres de la grilla de TV en vivo de
# directvgo.com). Cada canal de la guía lleva "dgo": true/false y el plugin oculta los que DGO no tiene. Sin el
# archivo no se marca nada y la guía muestra todos.
CANALES_DGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'canales_dgo.json')
# Nombre en la guía -> nombre en DGO, cuando no coinciden solos
EQUIVALENTES_DGO = {
    'TN': 'Todo Noticias.', 'C5N': 'C5N Canal 5 Noticias', 'A24': 'AMERICA 24', 'F24': 'France 24',
    'Atres Series': 'Atreseries', 'Nat Geo': 'National Geographic', 'Home & Health': 'Discovery Home & Health',
    'ID - Investigation Discovery': 'Discovery ID', 'Disney Junior': 'Disney Jr (Sur)',
    'Quiero': 'Quiero Musica en Mi Idioma',
}
# El mismo canal con dos nombres (las dos fuentes de open-epg los llaman distinto): se unen los que dan la misma clave
# de DGO (clave_dgo, con EQUIVALENTES_DGO). Queda el que tiene más programación, con este nombre si figura acá.
NOMBRE_UNIDO = {'america24': 'A24', 'cnn': 'CNN Internacional', 'foxsports': 'Fox Sports', 'disneyjr': 'Disney Junior',
                'discoveryhome&health': 'Discovery Home & Health', 'discoveryid': 'Discovery ID'}


def unir_duplicados(canales):
    """Une los canales repetidos. El que queda lleva en "otros_ids" los de los que se unieron (para "Mis canales")."""
    por_clave = {}
    for c in canales:
        por_clave.setdefault(clave_dgo(EQUIVALENTES_DGO.get(c['nombre'], c['nombre'])), []).append(c)
    salida = []
    for clave_canal, mismos in por_clave.items():
        if len(mismos) == 1:
            salida.append(mismos[0])
            continue
        queda = max(mismos, key=lambda c: len(c['programas']))
        queda['nombre'] = NOMBRE_UNIDO.get(clave_canal, queda['nombre'])
        queda['logo'] = queda.get('logo') or next((c['logo'] for c in mismos if c.get('logo')), '')
        queda['dgo'] = any(c.get('dgo') for c in mismos) if any('dgo' in c for c in mismos) else None
        if queda['dgo'] is None:
            del queda['dgo']
        queda['otros_ids'] = [c['id'] for c in mismos if c is not queda]
        print(f"uno {' + '.join(c['nombre'] for c in mismos)} -> {queda['nombre']}")
        salida.append(queda)
    return salida


ORDEN_GRUPOS = ['Aire', 'Noticias', 'Deportes', 'Películas y series', 'Infantiles', 'Documentales', 'Música',
                'Internacionales', 'Otros']


def bajar(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Vidrio-guia (Kodi)'})
    with urllib.request.urlopen(req, timeout=120) as r:
        datos = r.read()
    return gzip.decompress(datos) if url.endswith('.gz') else datos


def clave(nombre):
    """Nombre comparable: sin acentos, minúsculas, sin 'HD', '(ARG)', espacios ni signos."""
    t = unicodedata.normalize('NFD', nombre).encode('ascii', 'ignore').decode().lower()
    t = re.sub(r'\((arg|este|oeste|panregional|latinoamerica|sur)\)|\bhd\b|\.ar$', '', t)
    t = re.sub(r'\band\b', '&', t)
    t = re.sub(r'\b(channel|network|canal|en|la|el|tv)\b', '', t)  # "CNN En Español" = "CNN Español", "History Channel" = "History"
    return re.sub(r'[^a-z0-9+&]', '', t) or re.sub(r'[^a-z0-9]', '', nombre.lower())


def lindo(nombre):
    """'EL TRECE.ar' -> 'El Trece', respetando siglas."""
    n = re.sub(r'\.ar$', '', nombre).strip()
    n = n.replace("ESPAÍ'OL", 'ESPAÑOL').replace('ESPAÍ&apos;OL', 'ESPAÑOL')
    if n.upper() != n:
        return n
    palabras = []
    for p in n.split():
        palabras.append(p if p.upper() in SIGLAS or any(c.isdigit() for c in p) and len(p) <= 4 else p.capitalize())
    return ' '.join(palabras).replace('Tyc', 'TyC').replace('Ln+', 'LN+')


def clave_dgo(nombre):
    """Como clave(), sin el país o la región que DGO agrega al nombre ("ESPN 2 Argentina", "Space (Sur)")."""
    return clave(re.sub(r'\b(argentina|arg|sur|south|colombia|internacional)\b|[()]', '', nombre, flags=re.I))


def canales_de_dgo():
    try:
        with open(CANALES_DGO, encoding='utf-8') as fh:
            return {clave_dgo(n) for n in json.load(fh)['canales']}
    except (OSError, ValueError, KeyError):
        return None


def grupo(nombre):
    n = nombre.lower()
    for g, patron in GRUPOS:
        if re.search(patron, n):
            return g
    return 'Otros'


def epoch(valor):
    """'20261123191500 +0000' -> segundos."""
    return int(datetime.strptime(valor.strip(), '%Y%m%d%H%M%S %z').timestamp())


def logos():
    try:
        xml = bajar(LOGOS).decode('utf-8')
    except Exception as e:
        print(f'aviso: sin logos ({e})', file=sys.stderr)
        return {}
    out = {}
    for logo, nombre in re.findall(r'logo="([^"]+)"[^>]*>([^<]+)</channel>', xml):
        out.setdefault(clave(nombre.replace('&amp;', '&')), logo)
    return out


def main():
    ahora = int(time.time())
    canales, vistos = {}, set()
    for url in FUENTES:
        try:
            datos = bajar(url)
            # XML de terceros: un XMLTV no necesita DOCTYPE ni entidades propias (evita XXE y "billion laughs")
            if b'<!DOCTYPE' in datos[:4096] or b'<!ENTITY' in datos:
                raise ValueError('el XML trae DOCTYPE o ENTITY')
            raiz = ET.fromstring(datos)
        except Exception as e:
            print(f'aviso: no pude leer {url} ({e})', file=sys.stderr)
            continue
        for ch in raiz.findall('channel'):
            cid = ch.get('id')
            if cid in canales or not cid:
                continue
            nombre = lindo(ch.findtext('display-name') or cid)
            if nombre.lower() in OCULTOS:
                continue
            canales[cid] = {'id': cid, 'nombre': nombre, 'programas': []}
        for p in raiz.findall('programme'):
            c = canales.get(p.get('channel'))
            if not c or (p.get('channel'), p.get('start')) in vistos:
                continue
            vistos.add((p.get('channel'), p.get('start')))
            try:
                inicio, fin = epoch(p.get('start')), epoch(p.get('stop'))
            except (TypeError, ValueError):
                continue
            if fin < ahora - ANTES or inicio > ahora + DESPUES:
                continue
            titulo = (p.findtext('title') or '').strip()
            if not titulo or titulo.lower() == 'no data':
                continue
            c['programas'].append({'inicio': inicio, 'fin': fin, 'titulo': titulo,
                                   'sinopsis': (p.findtext('desc') or '').strip()})

    # Sin duplicados en HD: si está "ESPN 6" no hace falta "ESPN 6 HD"
    por_clave = {}
    for c in canales.values():
        if not c['programas']:
            continue
        k = clave(c['nombre'])
        previo = por_clave.get(k)
        if previo is None or (' HD' in previo['nombre'] and ' HD' not in c['nombre']):
            por_clave[k] = c
    logo = logos()
    dgo = canales_de_dgo()
    salida = []
    for k, c in por_clave.items():
        c['nombre'] = re.sub(r'\s+HD$', '', c['nombre'])
        c['programas'].sort(key=lambda p: p['inicio'])
        c['logo'] = logo.get(k, '')
        c['grupo'] = grupo(c['nombre'])
        if dgo is not None:
            c['dgo'] = clave_dgo(EQUIVALENTES_DGO.get(c['nombre'], c['nombre'])) in dgo
        salida.append(c)
    salida = unir_duplicados(salida)
    primero = {n.lower(): i for i, n in enumerate(PRIMERO)}
    salida.sort(key=lambda c: (ORDEN_GRUPOS.index(c['grupo']), primero.get(c['nombre'].lower(), len(primero)),
                               c['nombre'].lower()))

    guia = {'version': 1, 'generado': ahora, 'grupos': [g for g in ORDEN_GRUPOS if any(c['grupo'] == g for c in salida)],
            'canales': salida}
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    parcial = SALIDA + '.tmp'
    with open(parcial, 'w', encoding='utf-8') as fh:
        json.dump(guia, fh, ensure_ascii=False, separators=(',', ':'))
    os.chmod(parcial, 0o644)
    os.replace(parcial, SALIDA)
    print(f"guía: {len(salida)} canales ({sum(1 for c in salida if c['logo'])} con logo), "
          f"{sum(len(c['programas']) for c in salida)} programas; "
          + ', '.join(f"{g} {sum(1 for c in salida if c['grupo'] == g)}" for g in guia['grupos']))
    if dgo is not None:
        print(f"en DGO: {sum(1 for c in salida if c.get('dgo'))} de {len(salida)}")


if __name__ == '__main__':
    main()
