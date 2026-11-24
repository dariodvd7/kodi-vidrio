#!/usr/bin/env python3
"""Partidos en vivo para la fila "Deportes en vivo" del inicio de Vidrio.

Solo estas competencias: fútbol argentino (Primera División, Copa Argentina), Copa Libertadores, Copa Sudamericana y
NFL. Qué se está jugando sale del marcador público de ESPN (site.api.espn.com, sin cuenta ni clave); en qué canal se
ve, de la guía (guia.json, armada por guia.py): el canal cuyo programa al aire nombra a los dos equipos o, si la guía
dice solo "Liga Profesional 2026", el que nombra la competencia y empezó cerca del partido.

Escribe /srv/kodi-addons/vidrio/partidos.json (la carpeta compartida KodiAddons, al lado de guia.json). El plugin lo
lee cada minuto y muestra los partidos que tienen canal; elegir uno abre ese canal en DGO.

Uso (cron cada 2 minutos): partidos.py   |   partidos.py --mostrar (solo imprime, no escribe)
"""
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
import urllib.request
from datetime import datetime

CARPETA = '/srv/kodi-addons/vidrio'
GUIA = os.path.join(CARPETA, 'guia.json')
SALIDA = os.path.join(CARPETA, 'partidos.json')
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/{}/scoreboard'

# (ruta en ESPN, nombre en Vidrio, cómo la nombra la guía)
COMPETENCIAS = [
    ('soccer/arg.1', 'Primera División', r'primera division|liga profesional|\blpf\b|torneo (clausura|apertura)|futbol argentino'),
    ('soccer/arg.copa', 'Copa Argentina', r'copa argentina'),
    ('soccer/conmebol.libertadores', 'Copa Libertadores', r'libertadores'),
    ('soccer/conmebol.sudamericana', 'Copa Sudamericana', r'sudamericana'),
    ('football/nfl', 'NFL', r'\bnfl\b|futbol americano'),
]
# Programas que hablan del partido pero no lo pasan
NO_ES_EL_PARTIDO = re.compile(r'resumen|previa|magazine|show de|semanal|\bf10\b|highlights|lo mejor', re.I)
# Palabras que no sirven para reconocer a un equipo
COMUNES = {'de', 'del', 'la', 'el', 'los', 'las', 'y', 'club', 'atletico', 'atl', 'cf', 'fc', 'ca', 'sc', 'cd',
           'deportivo', 'sport', 'sporting', 'esgrima', 'juniors', 'san', 'santa', 'city', 'united', 'plate'}


def normalizar(texto):
    texto = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', texto).strip()


def palabras_equipo(equipo):
    nombres = ' '.join(equipo.get(k) or '' for k in ('displayName', 'shortDisplayName', 'name', 'location'))
    return {p for p in normalizar(nombres).split() if len(p) >= 3 and p not in COMUNES}


def nombra(texto_normalizado, palabras):
    return bool(palabras & set(texto_normalizado.split()))


def bajar(ruta):
    with urllib.request.urlopen(ESPN.format(ruta), timeout=20) as r:
        return json.load(r)


def en_vivo():
    """Partidos que ESPN da como en juego (incluye el entretiempo)."""
    partidos = []
    for ruta, nombre, patron in COMPETENCIAS:
        try:
            datos = bajar(ruta)
        except Exception as e:
            print(f'{nombre}: no pude leer ESPN ({e})', file=sys.stderr)
            continue
        for ev in datos.get('events', []):
            estado = ev.get('status', {})
            if estado.get('type', {}).get('state') != 'in':
                continue
            comp = ev['competitions'][0]
            equipos = sorted(comp['competitors'], key=lambda c: c.get('homeAway') != 'home')  # local primero
            partidos.append({
                'id': ev['id'], 'competencia': nombre, 'patron': patron,
                'inicio': int(datetime.fromisoformat(ev['date'].replace('Z', '+00:00')).timestamp()),
                'estado': estado.get('type', {}).get('shortDetail', ''),
                'reloj': estado.get('displayClock', ''),
                'equipos': [{'nombre': (c['team'].get('shortDisplayName') or c['team'].get('displayName') or '').strip(),
                             'completo': c['team'].get('displayName'), 'logo': c['team'].get('logo', ''),
                             'goles': c.get('score', ''), 'palabras': palabras_equipo(c['team'])}
                            for c in equipos],
            })
    return partidos


def canales_del_partido(partido, guia, ahora):
    """Canales de la guía que lo están pasando, del más seguro al menos."""
    patron = re.compile(partido['patron'])
    candidatos = []
    for canal in guia.get('canales', []):
        for p in canal.get('programas', []):
            if not (p['inicio'] <= ahora + 300 and ahora < p['fin']):
                continue
            titulo = normalizar(p.get('titulo'))
            texto = titulo + ' ' + normalizar(p.get('sinopsis'))
            local, visita = (nombra(texto, e['palabras']) for e in partido['equipos'])
            de_la_competencia = bool(patron.search(texto))
            if local and visita:
                puntos = 3
            elif (local or visita) and de_la_competencia:
                puntos = 2
            elif de_la_competencia and abs(p['inicio'] - partido['inicio']) <= 1800:
                puntos = 1
            else:
                continue
            if NO_ES_EL_PARTIDO.search(titulo) or 'relato' in titulo:
                puntos -= 1
            if puntos > 0:
                candidatos.append((puntos, canal.get('dgo') is not False, canal, p))
    candidatos.sort(key=lambda c: (-c[0], not c[1]))
    if candidatos:  # solo los más seguros: si uno nombra a los dos equipos, los que solo nombran la liga sobran
        mejor = candidatos[0][0]
        candidatos = [c for c in candidatos if c[0] == mejor]
    vistos, canales = set(), []
    for _, _, canal, p in candidatos:
        if canal['id'] not in vistos:
            vistos.add(canal['id'])
            canales.append({'id': canal['id'], 'nombre': canal['nombre'], 'logo': canal.get('logo', ''),
                            'dgo': canal.get('dgo'), 'programa': p.get('titulo', '')})
    return canales


def armar():
    ahora = time.time()
    try:
        with open(GUIA, encoding='utf-8') as fh:
            guia = json.load(fh)
    except (OSError, ValueError) as e:
        print(f'no pude leer la guía ({e})', file=sys.stderr)
        guia = {'canales': []}
    salida = []
    for partido in en_vivo():
        canales = canales_del_partido(partido, guia, ahora)
        for e in partido['equipos']:
            del e['palabras']
        del partido['patron']
        partido['canales'] = canales
        salida.append(partido)
    return {'generado': int(ahora), 'partidos': salida}


def main():
    datos = armar()
    if '--mostrar' in sys.argv:
        print(json.dumps(datos, ensure_ascii=False, indent=1))
        return
    # Se escribe aparte y se cambia de lugar: Kodi nunca lee un archivo a medias
    fd, tmp = tempfile.mkstemp(dir=CARPETA, prefix='.partidos-')
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        json.dump(datos, fh, ensure_ascii=False)
    os.chmod(tmp, 0o644)
    os.replace(tmp, SALIDA)


if __name__ == '__main__':
    main()
