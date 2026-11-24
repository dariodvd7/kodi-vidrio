# -*- coding: utf-8 -*-
"""Copias locales en el perfil del plugin (catálogo, guía, Trakt) a prueba de procesos simultáneos.

La skin pide varias filas a la vez y cada una es un proceso del plugin: si dos bajan el catálogo o la guía al mismo
tiempo y escriben el mismo archivo temporal, se pisan y queda un JSON cortado. Cada proceso usa su propio temporal y,
si una copia está dañada, se descarta en lugar de cortar la lista con un error.
"""
import json
import os
import threading
import uuid


def leer(ruta):
    """El JSON guardado, o None si no está o está dañado (en ese caso lo borra)."""
    try:
        with open(ruta, encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        try:
            os.remove(ruta)
        except OSError:
            pass
        return None


def escribir(ruta, datos):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = f'{ruta}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:8]}.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(datos, fh, ensure_ascii=False)
        os.replace(tmp, ruta)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
