# -*- coding: utf-8 -*-
"""Lo que el servicio hace con un video del catálogo mientras se reproduce.

1. Audio original: unos segundos después de arrancar, elige la pista de audio en el idioma original de la película o
   serie (el campo "idioma" del catálogo: "English" del homelab o "en" de TMDb). Kodi, con "audio: el del archivo",
   toma la primera pista, que en muchos archivos es el doblaje.
2. Siguiente episodio: en los últimos 15 segundos de un episodio muestra un cartel con el siguiente y una cuenta
   regresiva ("Ver ahora" / "Cancelar"). Al llegar a cero, o al terminar el episodio, reproduce el siguiente por el
   plugin (con sus datos y los códigos de Trakt). Cancelar o Atrás lo deja terminar y volver al inicio como siempre.
"""
import json
import time
from urllib.parse import quote_plus, unquote

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon('plugin.video.vidrio')
AVISO = 15          # segundos antes del final en que aparece el cartel
MINIMO = 300        # no ofrecer el siguiente en videos de menos de 5 minutos
ESPERA_AUDIO = 2.5  # segundos después de arrancar para elegir el audio (antes Kodi puede no tener las pistas)

# Idioma del catálogo -> códigos que Kodi da a las pistas (ISO 639-1 y 639-2, las dos variantes de 639-2).
IDIOMAS = {
    'english': ('en', 'eng'), 'spanish': ('es', 'spa'), 'portuguese': ('pt', 'por'),
    'french': ('fr', 'fre', 'fra'), 'german': ('de', 'ger', 'deu'), 'italian': ('it', 'ita'),
    'japanese': ('ja', 'jpn'), 'korean': ('ko', 'kor'), 'chinese': ('zh', 'chi', 'zho'),
    'mandarin': ('zh', 'chi', 'zho', 'cmn'), 'cantonese': ('zh', 'chi', 'zho', 'yue'),
    'hebrew': ('he', 'heb'), 'swedish': ('sv', 'swe'), 'danish': ('da', 'dan'),
    'norwegian': ('no', 'nor', 'nob', 'nb'), 'dutch': ('nl', 'dut', 'nld'), 'russian': ('ru', 'rus'),
    'polish': ('pl', 'pol'), 'turkish': ('tr', 'tur'), 'hindi': ('hi', 'hin'), 'thai': ('th', 'tha'),
    'finnish': ('fi', 'fin'), 'icelandic': ('is', 'ice', 'isl'), 'arabic': ('ar', 'ara'),
    'indonesian': ('id', 'ind'), 'greek': ('el', 'gre', 'ell'), 'czech': ('cs', 'cze', 'ces'),
    'hungarian': ('hu', 'hun'), 'ukrainian': ('uk', 'ukr'), 'catalan': ('ca', 'cat'), 'basque': ('eu', 'baq', 'eus'),
    'tagalog': ('tl', 'tgl', 'fil'), 'persian': ('fa', 'per', 'fas'), 'vietnamese': ('vi', 'vie'),
}
ATRAS = (9, 10, 92)  # parent dir, previous menu, back


def log(msg):
    xbmc.log(f'[vidrio.siguiente] {msg}', xbmc.LOGINFO)


def rpc(metodo, **params):
    r = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': metodo, 'params': params})))
    return r.get('result')


def codigos(idioma):
    """Códigos de pista para el idioma del catálogo, o un conjunto vacío si no se sabe."""
    idioma = (idioma or '').strip().lower()
    if not idioma:
        return set()
    if idioma in IDIOMAS:
        return set(IDIOMAS[idioma])
    corto = idioma.split('-')[0]
    for cods in IDIOMAS.values():
        if corto in cods:
            return set(cods)
    return {corto}


def elegir_pista(pistas, idioma):
    """La pista que corresponde al idioma original, o None. pistas: Player.GetProperties(audiostreams)."""
    cods = codigos(idioma)
    def comentario(p):
        nombre = (p.get('name') or '').lower()
        return 'comment' in nombre or 'comentario' in nombre
    pistas = [p for p in pistas if not comentario(p)]
    if cods:
        candidatas = [p for p in pistas if (p.get('language') or '').lower().split('-')[0] in cods]
    else:  # sin idioma en el catálogo: la que el archivo marca como original, si hay
        candidatas = [p for p in pistas if p.get('isoriginal')]
    if not candidatas:
        return None
    # entre las del idioma: la marcada original, después la marcada por defecto, después la de más canales
    return max(candidatas, key=lambda p: (bool(p.get('isoriginal')), bool(p.get('isdefault')), p.get('channels') or 0,
                                          -p.get('index', 0)))


def buscar(archivo):
    """{'idioma', 'siguiente'} del archivo en el catálogo, o None si no es del catálogo."""
    from resources.lib.catalogo import cargar
    cat = cargar()
    variantes = {archivo, unquote(archivo)}
    for p in cat.get('peliculas', []):
        if p.get('archivo') in variantes:
            return {'idioma': p.get('idioma', ''), 'siguiente': None}
    for s in cat.get('series', []):
        eps = [e for t in s.get('temporadas', []) for e in t.get('episodios', [])]
        actual = next((e for e in eps if e.get('archivo') in variantes), None)
        if not actual:
            continue
        def orden(e):
            return int(e.get('temporada') or 0), int(e.get('episodio') or 0)
        regulares = sorted((e for e in eps if (e.get('temporada') or 0) > 0), key=orden)
        proximo = None
        if (actual.get('temporada') or 0) > 0:
            proximo = next((e for e in regulares if orden(e) > orden(actual)), None)
        sig = None
        if proximo:
            repetido = (proximo.get('titulo') or '').strip().lower() == f"episodio {proximo.get('episodio')}"
            sig = {'archivo': proximo['archivo'], 'serie': s.get('titulo', ''),
                   'numero': f"T{proximo.get('temporada')} · E{proximo.get('episodio')}",
                   'titulo': '' if repetido else proximo.get('titulo', ''),
                   'imagen': proximo.get('imagen') or s.get('fanart') or s.get('dir', '') + 'fanart.jpg'}
        return {'idioma': s.get('idioma', ''), 'siguiente': sig}
    return None


class Cartel(xbmcgui.WindowXMLDialog):
    BOTON_AHORA, BOTON_CANCELAR = 10, 11

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.eleccion = ''

    def onInit(self):
        self.setFocusId(self.BOTON_AHORA)

    def onClick(self, control):
        self.eleccion = 'ahora' if control == self.BOTON_AHORA else 'cancelar'

    def onAction(self, accion):
        if accion.getId() in ATRAS:
            self.eleccion = 'cancelar'


class Siguiente:
    def __init__(self, player):
        self.player = player
        self.archivo = None
        self.info = None
        self.audio_en = 0.0
        self.cartel = None
        self.cancelado = False
        self.lanzado = False   # ya pedimos el siguiente: el "terminó" que viene es nuestro

    def reiniciar(self, archivo=None):
        self.cerrar()
        self.archivo, self.info, self.cancelado, self.lanzado = archivo, None, False, False
        self.audio_en = 0.0

    def cerrar(self):
        if self.cartel:
            try:
                self.cartel.close()
            except Exception:
                pass
            self.cartel = None

    def terminado(self, natural):
        """Lo llama el reproductor: natural=True si el video llegó al final, False si lo pararon."""
        if natural and self.info and self.info.get('siguiente') and self.cartel and not self.cancelado and not self.lanzado:
            self.lanzar()  # terminó antes de que la cuenta llegara a cero
            return
        self.cerrar()

    def lanzar(self):
        sig = self.info['siguiente']
        self.cerrar()
        self.lanzado = True
        log(f'siguiente episodio: {sig["serie"]} {sig["numero"]}')
        xbmc.executebuiltin(f'PlayMedia(plugin://plugin.video.vidrio/?reproducir={quote_plus(sig["archivo"])})')

    def elegir_audio(self):
        r = rpc('Player.GetProperties', playerid=1, properties=['audiostreams', 'currentaudiostream']) or {}
        pistas, actual = r.get('audiostreams') or [], r.get('currentaudiostream') or {}
        if len(pistas) < 2:
            return
        pista = elegir_pista(pistas, self.info.get('idioma'))
        if pista is None:
            log(f'audio: ninguna pista en {self.info.get("idioma") or "el idioma original"} '
                f'({", ".join(p.get("language") or "?" for p in pistas)})')
            return
        if pista.get('index') == actual.get('index'):
            return
        rpc('Player.SetAudioStream', playerid=1, stream=pista['index'])
        log(f'audio original: pista {pista["index"]} ({pista.get("language")}, {pista.get("name")}) '
            f'en vez de {actual.get("index")} ({actual.get("language")})')

    def paso(self):
        if not self.player.isPlayingVideo():
            if self.archivo and not self.lanzado:
                self.reiniciar()
            return
        try:
            actual = self.player.getPlayingFile()
        except RuntimeError:
            return
        if actual != self.archivo:
            self.reiniciar(actual)
            if not actual.startswith(('plugin://', 'http://', 'https://')):  # tráileres de YouTube y otros
                try:
                    self.info = buscar(actual)
                except Exception as e:
                    log(f'no pude buscar {actual} en el catálogo: {e}')
            if self.info:
                self.audio_en = time.time() + ESPERA_AUDIO
            return
        if not self.info:
            return
        if self.audio_en and time.time() >= self.audio_en:
            self.audio_en = 0.0
            if ADDON.getSettingBool('audio_original'):
                try:
                    self.elegir_audio()
                except Exception as e:
                    log(f'audio: error {e}')
        sig = self.info.get('siguiente')
        if not sig or self.cancelado or self.lanzado or not ADDON.getSettingBool('siguiente'):
            return
        try:
            total, pos = self.player.getTotalTime(), self.player.getTime()
        except RuntimeError:
            return
        resta = total - pos
        if self.cartel:
            if self.cartel.eleccion == 'ahora':
                return self.lanzar()
            if self.cartel.eleccion == 'cancelar':
                log('siguiente episodio: cancelado')
                self.cancelado = True
                return self.cerrar()
            if resta <= 0.8:
                return self.lanzar()
            self.cartel.setProperty('cuenta', str(max(1, int(resta + 0.5))))
            return
        if total >= MINIMO and 1 < resta <= AVISO:
            self.cartel = Cartel('vidrio-siguiente.xml', ADDON.getAddonInfo('path'), 'default', '1080i')
            for clave in ('serie', 'numero', 'titulo', 'imagen'):
                self.cartel.setProperty(clave, sig[clave])
            self.cartel.setProperty('cuenta', str(int(resta + 0.5)))
            self.cartel.show()
            log(f'cartel del siguiente episodio: {sig["serie"]} {sig["numero"]}')
