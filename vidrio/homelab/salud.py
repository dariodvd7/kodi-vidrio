#!/usr/bin/env python3
"""Control de salud de Vidrio en el homelab: avisa por correo si algo deja de andar.

Revisa que el catálogo y la guía se estén actualizando (crons de catalogo.py y guia.py), que el repositorio de
add-ons (nginx, puerto 8099) responda y que la carpeta compartida (Samba) atienda. Manda un correo cuando algo empieza
a fallar, cuando se arregla y, si sigue fallando, un recordatorio por día. El correo sale por el puente de atvloadly
(contenedor atvloadly-mail-bridge, que ya tiene la cuenta SMTP): se le habla desde adentro del contenedor.

Uso (como root, desde cron cada hora):
  salud.py            revisa y avisa si cambió algo
  salud.py --mostrar  solo muestra el estado, sin mandar nada
  salud.py --prueba   manda un correo de prueba
La IP del homelab sale de VIDRIO_HOMELAB (por defecto la de ejemplo).
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

IP = os.environ.get('VIDRIO_HOMELAB', '192.168.1.50')
CARPETA = '/srv/kodi-addons/vidrio'
ESTADO = '/var/lib/vidrio-salud/estado.json'
PUENTE = 'atvloadly-mail-bridge'
RECORDATORIO = 24 * 3600


def edad_horas(ruta):
    return (time.time() - os.path.getmtime(ruta)) / 3600


def revisar_catalogo():
    ruta = os.path.join(CARPETA, 'catalogo.json')
    if not os.path.isfile(ruta):
        return 'no está catalogo.json'
    if edad_horas(ruta) > 30:
        return f'el catálogo no se actualiza hace {edad_horas(ruta):.0f} horas (el cron corre a las 04:15)'
    with open(ruta, encoding='utf-8') as fh:
        cat = json.load(fh)
    if not cat.get('peliculas') or not cat.get('series'):
        return f"el catálogo vino vacío ({len(cat.get('peliculas', []))} películas, {len(cat.get('series', []))} series)"
    return None


def revisar_guia():
    ruta = os.path.join(CARPETA, 'guia.json')
    if not os.path.isfile(ruta):
        return 'no está guia.json'
    if edad_horas(ruta) > 7:
        return f'la guía no se actualiza hace {edad_horas(ruta):.0f} horas (el cron corre cada 3)'
    with open(ruta, encoding='utf-8') as fh:
        guia = json.load(fh)
    ahora = time.time()
    al_aire = sum(1 for c in guia.get('canales', []) for p in c.get('programas', []) if p['inicio'] <= ahora < p['fin'])
    if al_aire < 20:
        return f'la guía tiene programación ahora para {al_aire} canales (la fuente open-epg puede haber cambiado)'
    return None


def revisar_repositorio():
    try:
        with urllib.request.urlopen(f'http://{IP}:8099/addons.xml', timeout=10) as r:
            indice = r.read().decode('utf-8', 'replace')
    except Exception as e:
        return f'el repositorio de actualizaciones no responde ({e})'
    if 'plugin.video.vidrio' not in indice:
        return 'el repositorio de actualizaciones no publica el plugin'
    return None


def revisar_samba():
    try:
        with socket.create_connection((IP, 445), timeout=5):
            pass
    except OSError as e:
        return f'la carpeta compartida (Samba) no atiende ({e})'
    return None


REVISIONES = {'catálogo': revisar_catalogo, 'guía': revisar_guia, 'repositorio': revisar_repositorio,
              'carpeta compartida': revisar_samba}


def revisar():
    fallas = {}
    for nombre, funcion in REVISIONES.items():
        try:
            problema = funcion()
        except Exception as e:
            problema = f'no se pudo revisar ({type(e).__name__}: {e})'
        if problema:
            fallas[nombre] = problema
    return fallas


def avisar(titulo, mensaje):
    """Por el puente de correo de atvloadly: un POST a sí mismo desde adentro de su contenedor."""
    codigo = ("import sys,urllib.request;"
              "urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8080',data=sys.stdin.buffer.read(),"
              "headers={'Content-Type':'application/json'}),timeout=60).read()")
    cuerpo = json.dumps({'title': f'Vidrio: {titulo}', 'message': mensaje}).encode('utf-8')
    subprocess.run(['docker', 'exec', '-i', PUENTE, 'python', '-c', codigo], input=cuerpo, check=True, timeout=90)


def main():
    fallas = revisar()
    if '--mostrar' in sys.argv:
        print(json.dumps(fallas, ensure_ascii=False, indent=1) if fallas else 'todo bien')
        return
    if '--prueba' in sys.argv:
        avisar('correo de prueba', 'El control de salud de Vidrio puede mandarte avisos.\n\nEstado ahora: '
               + ('; '.join(f'{k}: {v}' for k, v in fallas.items()) if fallas else 'todo bien') + '.')
        print('correo de prueba enviado')
        return
    try:
        with open(ESTADO, encoding='utf-8') as fh:
            antes = json.load(fh)
    except (OSError, ValueError):
        antes = {'fallas': {}, 'avisado': 0}
    nuevas = {k: v for k, v in fallas.items() if k not in antes['fallas']}
    arregladas = [k for k in antes['fallas'] if k not in fallas]
    ahora = time.time()
    lineas = [f'- {k}: {v}' for k, v in fallas.items()]
    if nuevas:
        avisar('algo dejó de andar', 'Falla:\n' + '\n'.join(lineas)
               + '\n\nLos detalles están en /var/log/kodi-*.log del homelab.')
        antes['avisado'] = ahora
    elif fallas and ahora - antes.get('avisado', 0) > RECORDATORIO:
        avisar('sigue fallando', 'Sigue fallando:\n' + '\n'.join(lineas))
        antes['avisado'] = ahora
    if arregladas:
        avisar('volvió a andar', 'Se arregló: ' + ', '.join(arregladas) + '.'
               + ('\n\nSigue fallando:\n' + '\n'.join(lineas) if fallas else ''))
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    with open(ESTADO, 'w', encoding='utf-8') as fh:
        json.dump({'fallas': fallas, 'avisado': antes.get('avisado', 0)}, fh, ensure_ascii=False)
    print(time.strftime('%Y-%m-%d %H:%M'), 'fallas:', fallas or 'ninguna')


if __name__ == '__main__':
    main()
