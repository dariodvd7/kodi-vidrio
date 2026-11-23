# Reemplazo minimo de _scproxy para Kodi 22 RC2 en tvOS: su Python 3.14 no trae este
# modulo de macOS y urllib.request lo importa en plataformas Apple ("No module named '_scproxy'").
# Responde "sin proxy configurado", que es lo correcto para el Apple TV.
def _get_proxy_settings():
    return {'exclude_simple': False, 'exceptions': []}


def _get_proxies():
    return {}
