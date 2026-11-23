# -*- coding: utf-8 -*-
"""Servicio de Vidrio.

1. Tráiler de fondo: con la skin Vidrio en el inicio, si el foco queda unos segundos sobre una película o serie
   que tiene tráiler, lo reproduce en modo ventana (la skin lo muestra arriba, con el borde inferior difuminado).
   Se corta al mover el foco o al salir del inicio. Nunca corta algo que no haya arrancado este servicio.
2. YouTube: le aplica un parche chico al add-on de YouTube para que su servidor local funcione en macOS/tvOS
   (ver PARCHE_YOUTUBE) y marca su asistente de configuración como hecho (si no, traba el primer tráiler).
3. Subtítulos: deja a Kodi y a a4kSubtitles configurados para usar subtítulos en español; si el video no los trae,
   a4kSubtitles los busca y descarga solo.
4. Trakt: al cortar o terminar algo que no sea un tráiler, unos segundos después (cuando script.trakt ya avisó a Trakt)
   borra la caché de Trakt de Vidrio y cambia Window(home).Property(Vidrio.Trakt): la skin recarga "Continuar viendo".
   También al volver Kodi de segundo plano o del reposo, y cada 5 minutos con el inicio en pantalla: así aparece lo
   que se vio en otro equipo.
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


def instalado(addon_id):
    # xbmcaddon.Addon() con un add-on que no está deja un "EXCEPTION: Unknown addon id" en el log de Kodi aunque
    # se atrape el error: preguntar antes.
    return xbmc.getCondVisibility(f'System.HasAddon({addon_id})')


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
    if not instalado('plugin.video.youtube'):
        return False
    try:
        yt = xbmcaddon.Addon('plugin.video.youtube')
    except RuntimeError:
        return False
    if not ADDON.getSettingBool('trailers'):
        return False
    # El asistente de configuración de YouTube aparece la primera vez que se reproduce algo (en un Kodi nuevo, el
    # primer tráiler de fondo) y deja esa reproducción colgada: solo se ve un error de conexión con su servidor HTTP
    # local. Sus valores por defecto ya sirven para los tráileres, así que se marca como hecho. YouTube lo vuelve a
    # mostrar si forced_runs es anterior a la fecha de su versión: se pone la fecha actual.
    if yt.getSetting('kodion.setup_wizard') != 'false':
        yt.setSetting('kodion.setup_wizard', 'false')
        log('YouTube: asistente de configuración marcado como hecho')
    try:
        corridas = int(yt.getSetting('kodion.setup_wizard.forced_runs') or 0)
    except ValueError:
        corridas = 0
    if corridas < 1767970800:  # fecha que usa YouTube 7.4 (10/01/2026)
        yt.setSetting('kodion.setup_wizard.forced_runs', str(int(time.time())))
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
        if not instalado(A4K):
            raise RuntimeError(A4K)
        ajustes['subtitles.movie'] = A4K
        ajustes['subtitles.tv'] = A4K
        a4k = xbmcaddon.Addon(A4K)
        for clave in ('general.auto_search', 'general.auto_download', 'general.auto_select'):
            if a4k.getSetting(clave) != 'true':
                a4k.setSetting(clave, 'true')
    except RuntimeError:
        if not getattr(configurar_subtitulos, 'avisado', False):
            log('a4kSubtitles no está instalado: no hay búsqueda automática de subtítulos')
            configurar_subtitulos.avisado = True
    for clave, valor in ajustes.items():
        actual = rpc('Settings.GetSettingValue', setting=clave)
        if isinstance(actual, dict) and actual.get('value') != valor:
            log(f'{clave}: {actual.get("value")} -> {valor}: {rpc("Settings.SetSettingValue", setting=clave, value=valor)}')


def configurar_trakt():
    """Si está Trakt: que no cuente los tráileres de fondo (llegan por http), sí lo que reproduce Vidrio, y que no pida
    puntuar al terminar."""
    if not instalado('script.trakt'):
        return
    try:
        trakt = xbmcaddon.Addon('script.trakt')
    except RuntimeError:
        return
    # sin la pregunta "¿qué te pareció?" al terminar una película o un episodio
    for clave, valor in (('ExcludeHTTP', 'true'), ('ExcludePlugin', 'false'), ('rate_movie', 'false'),
                         ('rate_episode', 'false')):
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
        self.trakt_otra = 0.0   # segunda recarga de "Continuar viendo" después de vincular Trakt
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
            # Recién vinculada, Trakt a veces responde la lista vacía (y queda guardada 1 min): otra vuelta después.
            self.trakt_otra = time.time() + 70
        elif self.trakt_otra and time.time() >= self.trakt_otra:
            self.trakt_otra = 0.0
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


class Monitor(xbmc.Monitor):
    """Avisa cuando Kodi se despierta o sale el protector de pantalla: hay que recargar "Continuar viendo"."""
    def __init__(self):
        super().__init__()
        self.despierto = False

    def onNotification(self, sender, method, data):
        if method in ('System.OnWake', 'GUI.OnScreensaverDeactivated'):
            self.despierto = True


RECARGA_PERIODICA = 5 * 60  # con el inicio en pantalla y nada sonando


def buscar_actualizaciones(motivo):
    """Pide a Kodi que revise los repositorios ya, para que una versión nueva de Vidrio (repository.vidrio, en el
    homelab) llegue al abrir Kodi y no recién en la revisión diaria. Como mucho cada 30 minutos: al actualizarse, el
    servicio arranca de nuevo y no tiene que volver a pedirlo."""
    if not instalado('repository.vidrio'):
        return
    ultima = HOME.getProperty('Vidrio.ReposRevisados')
    if ultima and time.time() - float(ultima) < 30 * 60:
        return
    HOME.setProperty('Vidrio.ReposRevisados', str(time.time()))
    log(f'reviso los repositorios de add-ons ({motivo})')
    xbmc.executebuiltin('UpdateAddonRepos')


def recargar_trakt(trailers, motivo):
    log(f'recargo Continuar viendo ({motivo})')
    trailers.trakt_en = time.time()


def main():
    monitor = Monitor()
    if monitor.waitForAbort(5):
        return
    configurar_subtitulos()
    buscar_actualizaciones('Kodi arrancó')
    trailers = Trailers()
    vueltas = 0
    ultima_vuelta = time.time()
    ultima_recarga = ultima_vuelta - RECARGA_PERIODICA  # la primera vez que esté el inicio en pantalla (al arrancar o al actualizar el add-on)
    while not monitor.abortRequested():
        # Lo visto en otro equipo (Apple TV, TCL...) aparece al volver a Kodi: Android deja Kodi en segundo plano y
        # al volver el inicio no se recarga solo.
        ahora = time.time()
        if ahora - ultima_vuelta > 60:  # el servicio estuvo pausado: Kodi estaba en segundo plano o dormido
            recargar_trakt(trailers, 'Kodi volvió de segundo plano'); ultima_recarga = ahora
            buscar_actualizaciones('Kodi volvió de segundo plano')
        elif monitor.despierto:
            recargar_trakt(trailers, 'Kodi se despertó'); ultima_recarga = ahora
        elif (ahora - ultima_recarga > RECARGA_PERIODICA and xbmcgui.getCurrentWindowId() == 10000
              and not xbmc.Player().isPlaying()):
            recargar_trakt(trailers, 'cada 5 minutos en el inicio'); ultima_recarga = ahora
        monitor.despierto = False
        pedido = HOME.getProperty('Vidrio.Abrir')
        if pedido:  # abrir otra app (tvOS): desde acá, porque el servicio sigue vivo cuando tvOS responde
            HOME.clearProperty('Vidrio.Abrir')
            try:
                from resources.lib import abrir
                abrir.abrir_url(pedido)
            except Exception as e:
                log(f'abrir {pedido}: error {e}')
        ultima_vuelta = time.time()
        if vueltas % 1000 == 0:  # al arrancar y cada ~5 minutos: también toma add-ons instalados después
            configurar_trakt()
            if vueltas:
                configurar_subtitulos()
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
