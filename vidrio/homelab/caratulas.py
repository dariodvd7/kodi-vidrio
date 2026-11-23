#!/usr/bin/env python3
"""Copia el póster y el fondo que Radarr/Sonarr ya tienen en caché a cada carpeta
de película/serie como folder.jpg y fanart.jpg (para Kodi sin biblioteca).
No pisa imágenes existentes. Uso: sudo caratulas.py [--dry-run]"""
import json, os, re, shutil, sys, urllib.request
DRY = '--dry-run' in sys.argv
APPS = [('radarr', 7878, 'movie', '/mnt/media/peliculas'), ('sonarr', 8989, 'series', '/mnt/media/series')]
for app, port, ep, root in APPS:
    cfg = f'/mnt/media/docker/{app}'
    key = re.search(r'<ApiKey>(\w+)</ApiKey>', open(f'{cfg}/config.xml').read()).group(1)
    req = urllib.request.Request(f'http://127.0.0.1:{port}/api/v3/{ep}', headers={'X-Api-Key': key})
    items = json.load(urllib.request.urlopen(req, timeout=60))
    copied = skipped = 0; seen = set()
    for it in items:
        path = it.get('path') or ''
        if not os.path.isdir(path): continue
        seen.add(os.path.realpath(path)); st = os.stat(path)
        for src, dst in (('poster.jpg', 'folder.jpg'), ('fanart.jpg', 'fanart.jpg')):
            s, d = f'{cfg}/MediaCover/{it["id"]}/{src}', os.path.join(path, dst)
            if not os.path.isfile(s) or os.path.exists(d): skipped += 1; continue
            if not DRY:
                shutil.copyfile(s, d); os.chown(d, st.st_uid, st.st_gid); os.chmod(d, 0o644)
            copied += 1
    missing = [n for n in sorted(os.listdir(root)) if os.path.isdir(os.path.join(root, n))
               and os.path.realpath(os.path.join(root, n)) not in seen]
    print(f'{app}: {copied} copiadas, {skipped} ya estaban o sin imagen, {len(missing)} carpetas sin {app}')
    for n in missing: print('   sin datos:', n)
