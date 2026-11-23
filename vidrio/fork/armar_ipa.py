#!/usr/bin/env python3
"""Arma "Kodi Vidrio": el IPA oficial de Kodi para tvOS con Vidrio y los ajustes del Apple TV de casa ya puestos.

No recompila Kodi: toma el IPA sin firmar (el mismo que se instala con atvloadly) y le cambia el contenido.

  - Add-ons adentro de la app, registrados en system/addon-manifest.xml como opcionales (arrancan activos):
    skin y plugin Vidrio (de este repositorio), YouTube, Trakt, idioma español (Argentina) y sus dependencias (del
    repositorio oficial de Kodi 22, "piers"), y a4kSubtitles con su repositorio (fork/extra/).
  - Valores de fábrica de Kodi (system/settings/*.xml): skin Vidrio, español de Argentina, subtítulos en español,
    teclado de Kodi en lugar del de tvOS, sin cambio de frecuencia al reproducir, orígenes desconocidos y control
    remoto desde otros equipos (JSON-RPC en el puerto 9090) activados.
  - Python de la app: agrega _scproxy.py (el Python 3.14 del IPA no lo trae y urllib.request lo importa en
    plataformas Apple: "No module named '_scproxy'" en Trakt, requests, YouTube...).
  - YouTube con el parche de conexión local de Vidrio ya aplicado (adentro de la app no se puede escribir).
  - Se llama "Kodi Vidrio" y tiene otro identificador (org.xbmc.kodi-tvos.vidrio): se instala al lado del Kodi
    oficial, con sus propios datos, sin reemplazarlo.

El IPA que sale no está firmado: atvloadly lo firma al instalarlo, igual que el original.

El catálogo del plugin apunta a la IP del homelab de vidrio/local.json (fuera del repositorio; ver
local.ejemplo.json); con --generico queda la de ejemplo, 192.168.1.50 (así va el IPA publicado).

Uso: python3 armar_ipa.py [--ipa ../../Kodi-22.0rc2-tvos.ipa] [--salida ../dist/Kodi-Vidrio-22.0rc2.ipa] [--generico]
"""
import argparse
import ast
import gzip
import io
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
VIDRIO = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(VIDRIO, 'herramientas'))
import local  # noqa: E402  IP real del homelab (vidrio/local.json, fuera del repositorio)
REPO = 'https://mirrors.kodi.tv/addons/piers'
APP = 'Payload/Kodi.app'
NOMBRE = 'Kodi Vidrio'
BUNDLE_ID = 'org.xbmc.kodi-tvos.vidrio'  # distinto del oficial: no lo reemplaza
HOME = APP + '/AppData/AppHome'

# Lo que se pide al repositorio oficial; las dependencias se resuelven solas.
DEL_REPO = ['plugin.video.youtube', 'script.trakt', 'context.trakt.addtowatchlist', 'resource.language.es_ar']

# Valores de fábrica: archivo de system/settings -> {id del ajuste: valor por defecto}
AJUSTES = {
    'settings.xml': {
        'lookandfeel.skin': 'skin.vidrio',
        'locale.language': 'resource.language.es_ar',
        'locale.country': 'Argentina',
        'locale.subtitlelanguage': 'Spanish',
        'videoplayer.adjustrefreshrate': '0',
        'addons.unknownsources': 'true',
        'services.esallinterfaces': 'true',
    },
    'darwin_tvos.xml': {
        'input.tvosusekodikeyboard': 'true',
    },
}

SCPROXY = '''# Agregado por Kodi Vidrio: el Python 3.14 de Kodi para tvOS no trae este modulo de macOS y urllib.request lo
# importa en plataformas Apple ("No module named '_scproxy'"). Responde "sin proxy configurado".
def _get_proxy_settings():
    return {'exclude_simple': False, 'exceptions': []}


def _get_proxies():
    return {}
'''


def log(msg):
    print(msg, flush=True)


def bajar(url):
    # curl y no urllib: los espejos del repositorio redirigen a servidores cuya cadena de certificados el Python de
    # algunas instalaciones no valida; curl usa los certificados del sistema.
    r = subprocess.run(['curl', '-fsSL', '--retry', '3', '-A', 'Kodi-Vidrio-build', url], capture_output=True, timeout=300)
    if r.returncode:
        raise SystemExit(f'no pude bajar {url}: {r.stderr.decode(errors="ignore").strip()}')
    return r.stdout


def catalogo_repo():
    """{id: (version, [(dependencia, opcional)])} del repositorio oficial."""
    xml = gzip.decompress(bajar(REPO + '/addons.xml.gz')).decode('utf-8')
    addons = {}
    for bloque in re.findall(r'<addon\s.*?</addon>', xml, re.S):
        cab = re.match(r'<addon\s([^>]*)>', bloque).group(1)
        aid = re.search(r'\bid="([^"]+)"', cab).group(1)
        version = re.search(r'\bversion="([^"]+)"', cab).group(1)
        deps = [(d, 'optional="true"' in resto)
                for d, resto in re.findall(r'<import\s+addon="([^"]+)"([^>]*)/?>', bloque)]
        addons[aid] = (version, deps)
    return addons


def resolver(pedidos, repo, incluidos):
    """Ids a bajar del repositorio (pedidos y sus dependencias obligatorias que la app no trae)."""
    hace_falta, pendientes = [], list(pedidos)
    while pendientes:
        aid = pendientes.pop()
        if aid in hace_falta or aid in incluidos or aid.startswith(('xbmc.', 'kodi.')):
            continue
        if aid not in repo:
            raise SystemExit(f'{aid} no está en el repositorio oficial')
        hace_falta.append(aid)
        pendientes += [d for d, opcional in repo[aid][1] if not opcional]
    return hace_falta


def extraer_zip(datos, destino):
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        z.extractall(destino)


def cambiar_default(xml, ajuste, valor):
    patron = re.compile(r'(<setting id="' + re.escape(ajuste) + r'"[^>]*>.*?<default>)[^<]*(</default>)', re.S)
    nuevo, n = patron.subn(lambda m: m.group(1) + valor + m.group(2), xml, count=1)
    if not n:
        raise SystemExit(f'no encontré el valor por defecto de {ajuste}')
    return nuevo


def parche_youtube(raiz):
    """Aplica PARCHE_YOUTUBE del servicio de Vidrio al YouTube que va adentro de la app."""
    fuente = open(os.path.join(VIDRIO, 'plugin.video.vidrio', 'service.py'), encoding='utf-8').read()
    # Sin ejecutar service.py: MARCA_PARCHE es un texto y PARCHE_YOUTUBE es MARCA_PARCHE + otro texto.
    valores = {}
    for nodo in ast.parse(fuente).body:
        if not (isinstance(nodo, ast.Assign) and isinstance(nodo.targets[0], ast.Name)):
            continue
        nombre, v = nodo.targets[0].id, nodo.value
        if nombre == 'MARCA_PARCHE':
            valores[nombre] = ast.literal_eval(v)
        elif nombre == 'PARCHE_YOUTUBE' and isinstance(v, ast.BinOp) and isinstance(v.left, ast.Name):
            valores[nombre] = valores[v.left.id] + ast.literal_eval(v.right)
    ruta = os.path.join(raiz, 'resources/lib/youtube_plugin/kodion/network/http_server.py')
    codigo = open(ruta, encoding='utf-8').read()
    if valores['MARCA_PARCHE'] not in codigo:
        if '\ndef get_connect_address(' not in codigo:
            raise SystemExit('YouTube cambió: http_server.py ya no tiene get_connect_address')
        with open(ruta, 'a', encoding='utf-8') as fh:
            fh.write('\n\n' + valores['PARCHE_YOUTUBE'])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--ipa', default=os.path.join(VIDRIO, '..', 'Kodi-22.0rc2-tvos.ipa'))
    ap.add_argument('--salida', default=os.path.join(VIDRIO, 'dist', 'Kodi-Vidrio-22.0rc2.ipa'))
    ap.add_argument('--generico', action='store_true',
                    help='catálogo con la IP de ejemplo (para publicar), no la de vidrio/local.json')
    args = ap.parse_args()

    trabajo = tempfile.mkdtemp(prefix='kodi-vidrio-')
    try:
        log(f'1/6 abro {args.ipa}')
        with zipfile.ZipFile(args.ipa) as z:
            z.extractall(trabajo)
        addons_dir = os.path.join(trabajo, HOME, 'addons')
        incluidos = set(os.listdir(addons_dir))

        log('2/6 add-ons del repositorio oficial')
        repo = catalogo_repo()
        nuevos = []
        for aid in resolver(DEL_REPO, repo, incluidos):
            version = repo[aid][0]
            log(f'    {aid} {version}')
            for intento in range(5):  # cada pedido puede ir a otro espejo, y alguno a veces responde una página
                datos = bajar(f'{REPO}/{aid}/{aid}-{version}.zip')
                if zipfile.is_zipfile(io.BytesIO(datos)):
                    break
            else:
                raise SystemExit(f'{aid}: los espejos no devolvieron un zip válido')
            extraer_zip(datos, addons_dir)
            nuevos.append(aid)

        log('3/6 Vidrio y a4kSubtitles')
        for carpeta in ('skin.vidrio', 'plugin.video.vidrio'):
            destino = os.path.join(addons_dir, carpeta)
            shutil.copytree(os.path.join(VIDRIO, carpeta), destino,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
            nuevos.append(carpeta)
        log('    homelab del catálogo: ' + local.aplicar(os.path.join(addons_dir, 'plugin.video.vidrio'),
                                                         local.EJEMPLO if args.generico else None))
        for nombre in sorted(os.listdir(os.path.join(AQUI, 'extra'))):
            if nombre.endswith('.zip'):
                with zipfile.ZipFile(os.path.join(AQUI, 'extra', nombre)) as z:
                    raices = {n.split('/')[0] for n in z.namelist()}
                    z.extractall(addons_dir)
                nuevos += sorted(raices)
        parche_youtube(os.path.join(addons_dir, 'plugin.video.youtube'))

        log('4/6 manifiesto y valores de fábrica')
        manifiesto = os.path.join(trabajo, HOME, 'system', 'addon-manifest.xml')
        xml = open(manifiesto, encoding='utf-8').read()
        agregar = ''.join(f'  <addon optional="true">{a}</addon>\n' for a in sorted(set(nuevos))
                          if f'>{a}</addon>' not in xml)
        open(manifiesto, 'w', encoding='utf-8').write(xml.replace('</addons>', agregar + '</addons>'))
        for archivo, cambios in AJUSTES.items():
            ruta = os.path.join(trabajo, HOME, 'system', 'settings', archivo)
            xml = open(ruta, encoding='utf-8').read()
            for ajuste, valor in cambios.items():
                xml = cambiar_default(xml, ajuste, valor)
            open(ruta, 'w', encoding='utf-8').write(xml)

        log('5/6 Python (_scproxy) y nombre de la app')
        libpy = [d for d in os.listdir(os.path.join(trabajo, APP, 'lib')) if d.startswith('python3')]
        for d in libpy:
            open(os.path.join(trabajo, APP, 'lib', d, '_scproxy.py'), 'w', encoding='utf-8').write(SCPROXY)
        # Otro identificador: se instala al lado del Kodi oficial, con sus propios datos, sin reemplazarlo.
        # Las extensiones (Top Shelf) tienen que colgar del identificador nuevo.
        viejo = None
        for info in [os.path.join(trabajo, APP, 'Info.plist')] + \
                [os.path.join(r, 'Info.plist') for r, d, f in os.walk(os.path.join(trabajo, APP, 'PlugIns'))
                 if r.endswith('.appex') and 'Info.plist' in f]:
            with open(info, 'rb') as fh:
                binario = fh.read(6) == b'bplist'
            with open(info, 'rb') as fh:
                plist = plistlib.load(fh)
            ident = plist['CFBundleIdentifier']
            if viejo is None:  # la app principal va primero
                viejo = ident
                plist['CFBundleIdentifier'] = BUNDLE_ID
                plist['CFBundleDisplayName'] = NOMBRE
                plist['CFBundleName'] = NOMBRE
            elif ident.startswith(viejo + '.'):
                plist['CFBundleIdentifier'] = BUNDLE_ID + ident[len(viejo):]
            with open(info, 'wb') as fh:
                plistlib.dump(plist, fh, fmt=plistlib.FMT_BINARY if binario else plistlib.FMT_XML)
            log(f'    {ident} -> {plist["CFBundleIdentifier"]}')

        log(f'6/6 armo {args.salida}')
        os.makedirs(os.path.dirname(os.path.abspath(args.salida)), exist_ok=True)
        tmp = args.salida + '.tmp'
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for raiz, dirs, archivos in os.walk(os.path.join(trabajo, 'Payload')):
                dirs.sort()
                for nombre in sorted(archivos):
                    ruta = os.path.join(raiz, nombre)
                    rel = os.path.relpath(ruta, trabajo)
                    if os.path.islink(ruta):  # conservar enlaces simbólicos de los frameworks
                        zi = zipfile.ZipInfo(rel)
                        zi.create_system = 3
                        zi.external_attr = 0o120777 << 16
                        z.writestr(zi, os.readlink(ruta))
                    else:
                        z.write(ruta, rel)
        os.replace(tmp, args.salida)
        log(f'listo: {len(set(nuevos))} add-ons agregados, {os.path.getsize(args.salida) / 1e6:.0f} MB')
    finally:
        shutil.rmtree(trabajo, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
