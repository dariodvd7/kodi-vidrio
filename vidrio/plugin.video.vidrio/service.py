# -*- coding: utf-8 -*-
"""Servicio de Vidrio.

1. Tráiler de fondo: con la skin Vidrio en el inicio, si el foco queda unos segundos sobre una película o serie
   que tiene tráiler, lo reproduce en modo ventana (la skin lo muestra arriba, con el borde inferior difuminado).
   Se corta al mover el foco o al salir del inicio. Nunca corta algo que no haya arrancado este servicio.
2. YouTube: le aplica un parche chico al add-on de YouTube para que su servidor local funcione en macOS/tvOS
   (ver PARCHE_YOUTUBE).
3. Subtítulos: deja a Kodi y a a4kSubtitles configurados para usar subtítulos en español; si el video no los trae,
   a4kSubtitles los busca y descarga solo.
4. Trakt: al cortar o terminar algo que no sea un tráiler, unos segundos después (cuando script.trakt ya avisó a Trakt)
   borra la caché de Trakt de Vidrio y cambia Window(home).Property(Vidrio.Trakt): la skin recarga "Continuar viendo".
"""
import json
import time

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon('plugin.video.vidrio')
FILAS = range(5100, 5111)  # ids de las filas del inicio en la skin (5100 = Continuar viendo)
HOME = xbmcgui.Window(10000)
A4K = 'service.subtitles.a4ksubtitles'


def log(msg):
    xbmc.log(f'[vidrio.servicio] {msg}', xbmc.LOGINFO)


def rpc(metodo, **params):
    r = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': metodo, 'params': params})))
    return r.get('result', r.get('error'))


MARCA_PARCHE = '# --- parche Vidrio: conexión local en macOS/tvOS ---'
PARCHE_YOUTUBE = MARCA_PARCHE + '''
# En macOS y tvOS, conectar un socket UDP al puerto 0 falla (Errno 49), así que get_connect_address termina usando
# xbmc.getIPAddress(), que en el Apple TV puede ser una IP que no conecta, y el manifiesto del tráiler no se baja.
# Si el servidor escucha en la dirección local, se usa esa misma dirección. Lo agrega plugin.video.vidrio.
_vidrio_get_connect_address = get_connect_address


def get_connect_address(context, as_netloc=False, address=None):
    if address is None:
        _settings = context.get_settings()
        _escucha, _puerto = _settings.httpd_listen(), _settings.httpd_port()
    else:
        _escucha, _puerto = address
    if _escucha in ('127.0.0.1', '::1'):
        if as_netloc:
            return ':'.join(('[::1]' if _escucha == '::1' else _escucha, str(_puerto)))
        return _escucha, _puerto
    return _vidrio_get_connect_address(context, as_netloc=as_netloc, address=address)
'''


def parchear_youtube():
    """Deja el add-on de YouTube usable para tráileres en macOS/tvOS (ver PARCHE_YOUTUBE). Se reaplica solo si
    YouTube se actualiza y pisa el archivo. Devuelve True si cambió algo (hace falta reiniciar Kodi)."""
    import xbmcvfs
    try:
        yt = xbmcaddon.Addon('plugin.video.youtube')
    except RuntimeError:
        return False
    if not ADDON.getSettingBool('trailers'):
        return False
    ruta = xbmcvfs.translatePath(yt.getAddonInfo('path')) + \
        '/resources/lib/youtube_plugin/kodion/network/http_server.py'
    cambio = False
    try:
        with open(ruta, encoding='utf-8') as fh:
            codigo = fh.read()
        if MARCA_PARCHE not in codigo and '\ndef get_connect_address(' in codigo:
            with open(ruta, 'a', encoding='utf-8') as fh:
                fh.write('\n\n' + PARCHE_YOUTUBE)
            log('YouTube: parche de conexión local aplicado')
            cambio = True
    except OSError as e:
        log(f'YouTube: no pude aplicar el parche ({e})')
        return False
    if yt.getSetting('kodion.http.listen') != '127.0.0.1':
        yt.setSetting('kodion.http.listen', '127.0.0.1')
        log('YouTube: servidor local en 127.0.0.1')
        cambio = True
    return cambio


def configurar_subtitulos():
    if not ADDON.getSettingBool('subtitulos'):
        return
    ajustes = {
        'locale.subtitlelanguage': 'Spanish',           # idioma preferido de subtítulos
        'subtitles.languages': ['Spanish', 'English'],  # idiomas a buscar, en orden
    }
    try:
        xbmcaddon.Addon(A4K)
        ajustes['subtitles.movie'] = A4K
        ajustes['subtitles.tv'] = A4K
        a4k = xbmcaddon.Addon(A4K)
        for clave in ('general.auto_search', 'general.auto_download', 'general.auto_select'):
            if a4k.getSetting(clave) != 'true':
                a4k.setSetting(clave, 'true')
    except RuntimeError:
        log('a4kSubtitles no está instalado: no hay búsqueda automática de subtítulos')
    for clave, valor in ajustes.items():
        actual = rpc('Settings.GetSettingValue', setting=clave)
        if isinstance(actual, dict) and actual.get('value') != valor:
            log(f'{clave}: {actual.get("value")} -> {valor}: {rpc("Settings.SetSettingValue", setting=clave, value=valor)}')


def configurar_trakt():
    """Si está Trakt: que no cuente los tráileres de fondo (llegan por http) y sí lo que reproduce Vidrio."""
    try:
        trakt = xbmcaddon.Addon('script.trakt')
    except RuntimeError:
        return
    for clave, valor in (('ExcludeHTTP', 'true'), ('ExcludePlugin', 'false')):
        if trakt.getSetting(clave) != valor:
            trakt.setSetting(clave, valor)
            log(f'Trakt: {clave} = {valor}')


class Reproductor(xbmc.Player):
    def __init__(self, servicio):
        super().__init__()
        self.servicio = servicio

    def onAVStarted(self):
        self.servicio.al_empezar()

    def onPlayBackEnded(self):
        self.servicio.al_terminar(evento=True)

    def onPlayBackStopped(self):
        self.servicio.al_terminar(evento=True)

    def onPlayBackError(self):
        self.servicio.al_fallar()


class Trailers:
    def __init__(self):
        self.candidato = ''     # tráiler del título con foco
        self.desde = 0.0        # desde cuándo tiene foco
        self.pedido = ''        # tráiler que mandamos a reproducir y todavía no arrancó
        self.archivo = None     # archivo que está sonando y arrancamos nosotros
        self.vistos = set()     # no repetir el mismo tráiler mientras el foco no se mueva
        self.pedido_desde = 0.0
        self.fila = None        # última fila con foco
        self.fallos = 0         # tráileres que no arrancaron en esta sesión
        self.trakt_en = 0.0     # cuándo recargar "Continuar viendo" (después de ver algo que no sea un tráiler)
        self.completa = None    # último video del usuario que ya pasamos a pantalla completa
        self.vinculado = None   # si script.trakt tiene cuenta vinculada (para recargar la fila al vincularla)
        self.revisado = 0.0
        self.player = Reproductor(self)

    def apagado(self):
        # Si los tráileres fallan dos veces seguidas (por ejemplo, el add-on de YouTube no anda), no insistir en
        # esta sesión: cada intento fallido muestra un cartel de error encima del inicio.
        return self.fallos >= 2

    def al_fallar(self):
        if self.pedido:
            self.fallos += 1
            log(f'el tráiler no arrancó ({self.fallos})' + (': tráileres en pausa hasta reiniciar Kodi' if self.apagado() else ''))
        self.al_terminar()

    def al_empezar(self):
        try:
            actual = self.player.getPlayingFile()
        except RuntimeError:
            return
        if self.pedido:
            self.archivo, self.pedido = actual, ''
            self.fallos = 0
            HOME.setProperty('Vidrio.Preview', '1')
            log('tráiler en pantalla')
        elif actual != self.archivo:  # el usuario puso otra cosa: ya no es nuestro
            self.archivo = None
            HOME.clearProperty('Vidrio.Preview')

    def al_terminar(self, evento=False):
        # Mientras YouTube resuelve el tráiler, Kodi puede avisar "terminó" por el plugin:// antes de que arranque el
        # video real: ese aviso no cancela el pedido (lo cancelan el error, el tiempo de espera o mover el foco).
        if evento and self.pedido and not self.archivo:
            return
        if evento and not self.archivo and not self.pedido:  # terminó algo del usuario, no un tráiler nuestro
            self.trakt_en = time.time() + 8
        self.archivo, self.pedido = None, ''
        HOME.clearProperty('Vidrio.Preview')

    def es_nuestro(self):
        if not self.archivo or not self.player.isPlaying():
            return False
        try:
            return self.player.getPlayingFile() == self.archivo
        except RuntimeError:
            return False

    def cortar(self):
        if self.pedido and not self.archivo and self.player.isPlaying():  # todavía resolviendo: es nuestro
            self.player.stop()
        if self.es_nuestro():
            log(f'corto el tráiler (ventana {xbmcgui.getCurrentWindowId()}, diálogo {xbmcgui.getCurrentWindowDialogId()}, control {xbmc.getInfoLabel("System.CurrentControlId")!r})')
            self.player.stop()
        self.al_terminar()

    def foco(self):
        """Tráiler del elemento con foco en una fila del inicio, o '' si no corresponde."""
        if xbmc.getSkinDir() != 'skin.vidrio' or xbmcgui.getCurrentWindowId() != 10000:
            return None
        if xbmcgui.getCurrentWindowDialogId() not in (9999, 10138, 10160):  # 10138/10160 = diálogos de ocupado
            return None
        for cid in FILAS:
            if xbmc.getCondVisibility(f'Control.HasFocus({cid})'):
                self.fila = cid
                return xbmc.getInfoLabel(f'Container({cid}).ListItem.Property(vidrio.trailer)')
        # Al arrancar el video en modo ventana Kodi a veces deja el inicio sin foco: devolverlo a la misma fila.
        if self.fila and not xbmc.getInfoLabel('System.CurrentControlId') and (self.pedido or self.archivo):
            xbmc.executebuiltin(f'SetFocus({self.fila})')
            return self.candidato
        return ''

    def pantalla_completa(self):
        # PlayMedia desde el inicio (por ejemplo "Continuar viendo") deja el video detrás del inicio: se oye pero no se
        # ve. Al arrancar un video del usuario con el inicio en pantalla, pasarlo a pantalla completa una sola vez
        # (si después vuelve al inicio a propósito, no se lo forzamos de nuevo).
        if not self.player.isPlaying():
            self.completa = None
            return
        if self.archivo or self.pedido or not self.player.isPlayingVideo():
            return
        try:
            actual = self.player.getPlayingFile()
        except RuntimeError:
            return
        if actual and actual != self.completa:
            self.completa = actual
            if xbmcgui.getCurrentWindowId() == 10000:
                log('paso el video a pantalla completa')
                xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')

    def revisar_trakt(self):
        # La fila "Continuar viendo" se carga al abrir el inicio: si la cuenta se vincula (o desvincula) después,
        # recargarla en ese momento y no recién al terminar de ver algo.
        if time.time() - self.revisado < 10:
            return
        self.revisado = time.time()
        from resources.lib import trakt
        vinculado = trakt.credenciales() is not None
        if self.vinculado is not None and vinculado != self.vinculado:
            log('Trakt ' + ('vinculado' if vinculado else 'desvinculado') + ': recargo Continuar viendo')
            self.trakt_en = time.time()
        self.vinculado = vinculado

    def paso(self):
        self.pantalla_completa()
        self.revisar_trakt()
        if self.trakt_en and time.time() >= self.trakt_en:
            self.trakt_en = 0.0
            from resources.lib import trakt
            trakt.borrar()
            HOME.setProperty('Vidrio.Trakt', str(int(time.time())))
            log('recargo Continuar viendo')
        # Además del aviso onAVStarted (que no siempre llega en modo ventana), detectar el arranque por sondeo.
        if self.pedido and not self.archivo and self.player.isPlayingVideo() and time.time() - self.pedido_desde > 1:
            self.al_empezar()
        if self.pedido and time.time() - self.pedido_desde > 30:  # pedido que nunca arrancó
            self.al_fallar()
        if not ADDON.getSettingBool('trailers') or self.apagado():
            if self.archivo:
                self.cortar()
            return
        trailer = self.foco()
        if trailer is None:  # fuera del inicio: el tráiler no sigue de fondo
            if self.archivo:
                self.cortar()
            return
        if trailer != self.candidato:
            if self.archivo or self.pedido:
                self.cortar()
            self.candidato, self.desde = trailer, time.time()
            self.vistos.discard(trailer)
            HOME.clearProperty('Vidrio.Preview')
            return
        espera = max(1, ADDON.getSettingInt('trailer_espera'))
        ocupado = self.player.isPlaying() and not self.es_nuestro()
        if (trailer and not self.archivo and not self.pedido and not ocupado and trailer not in self.vistos
                and time.time() - self.desde >= espera):
            log(f'tráiler de fondo: {trailer}')
            self.pedido, self.pedido_desde = trailer, time.time()
            self.vistos.add(trailer)
            xbmc.executebuiltin(f'PlayMedia({trailer},1)')  # 1 = modo ventana, no pasa a pantalla completa


def main():
    monitor = xbmc.Monitor()
    if monitor.waitForAbort(5):
        return
    configurar_subtitulos()
    trailers = Trailers()
    vueltas = 0
    while not monitor.abortRequested():
        if vueltas % 1000 == 0:
            configurar_trakt()
        if vueltas % 1000 == 0 and parchear_youtube():  # al arrancar y cada ~5 minutos (YouTube se actualiza solo)
            # reiniciar el add-on de YouTube para que su servicio levante el servidor con el parche
            rpc('Addons.SetAddonEnabled', addonid='plugin.video.youtube', enabled=False)
            monitor.waitForAbort(2)
            rpc('Addons.SetAddonEnabled', addonid='plugin.video.youtube', enabled=True)
            trailers.fallos = 0
        vueltas += 1
        try:
            trailers.paso()
        except Exception as e:  # el servicio no debe morir por un error puntual
            log(f'error: {e}')
        if monitor.waitForAbort(0.3):
            break
    HOME.clearProperty('Vidrio.Preview')


main()
