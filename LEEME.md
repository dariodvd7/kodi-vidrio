# Kodi en el Apple TV (Apple TV del living)

## Estado actual (2026-11-22) — Kodi 22 RC2 SIN biblioteca
- Instalado **Kodi 22.0 RC2** (última versión para tvOS) a pedido. Skins las instala el usuario: activa
  **Arctic Fuse 2** (también tiene Arctic Horizon 2 y Bald instaladas).
- Fuentes de video: `smb://192.168.1.50/Peliculas/` y `smb://192.168.1.50/Series/` (navegar por carpetas).
- **Sin biblioteca a propósito**: Kodi 22 RC2 en tvOS se cierra en cuanto la biblioteca tiene contenido, con
  cualquier skin (Estuary, Bald, Mistuary, Arctic Fuse 2) y aun con Bald Helper, texturemaker y TMDb Helper
  apagados. Sin biblioteca arranca y navega estable (probado en frío). **No usar "Actualizar biblioteca" ni
  escanear** (las carpetas siguen con tipo de contenido asignado; un escaneo volvería a romperlo).
- Scrapers arreglados para Kodi 22 instalados (3.2.2.2 / 2.0.9.1). Cuando salga Kodi 22 final, reintentar
  la biblioteca; si falla, volver a Kodi 21.3 (`Kodi-21.3-tvos.ipa`), que funcionó con todo.
- **TMDb Helper arreglado (2026-11-22)**: sus módulos fallaban por `_scproxy` (Python 3.14 de tvOS). Se instalaron
  `script.module.requests-2.31.0.1-kodi.zip` y `script.module.jurialmunkey-0.2.39.1-kodi.zip` (mismo código + stub
  `_scproxy.py`); arreglan a todos los addons que dependen de ellos. Si un repo trae una versión mayor sin el stub,
  vuelve el error: reinstalar estos zips desde `smb://192.168.1.50/KodiAddons/`.
- **Pantalla principal de Arctic Fuse 2**: los ítems Películas y Series del menú lateral apuntan a las carpetas del
  homelab (archivo `addon_data/script.skinvariables/nodes/skin.arctic.fuse.2/skinvariables-shortcut-sidemenu.json`,
  copia en `addons/`). También hay favoritos "Películas" y "Series".
- La interfaz de Kodi está en castellano.
- **Inicio de Arctic Fuse 2**: en "Discover" solo **Mis películas** y **Mis series** (carpetas del homelab, sin
  carátulas porque no hay biblioteca); se quitaron las filas de IMDb/TMDb y las de biblioteca ("New Movies", "New Episodes").
  Para cargar un menú editado: `route=copy_menufolder=<carpeta smb>&skin=skin.arctic.fuse.2&force=true` como primera
  acción del JSON de abajo. TMDb Helper en **Español (México)**.
- **Carátulas sin biblioteca (2026-11-22)**: `/opt/kodi-artwork/caratulas.py` en el homelab copia el póster y el fondo
  que Radarr/Sonarr tienen en caché (`/mnt/media/docker/{radarr,sonarr}/MediaCover/<id>/`) a cada carpeta como
  `folder.jpg` y `fanart.jpg`, sin pisar los que existan. Corre todos los días a las 04:15 (`/etc/cron.d/kodi-caratulas`,
  log en `/var/log/kodi-caratulas.log`). Primera pasada: 249 películas y 90 de 91 series ("The Pitt (Latino)" no está en
  Sonarr). Probar sin copiar: `sudo /opt/kodi-artwork/caratulas.py --dry-run`.
- **Reconstruir el menú del skin en Kodi 22**: `Addons.ExecuteAddon` abre script.skinvariables como plugin y no
  reconstruye. Lo que funcionó fue un JSON con acciones (`Skin.SetString(Shortcuts.RebuildDateTime,<fecha>)` y
  `route=action=buildtemplate&force=true&background=false&lastbuildtime=<fecha>`) cargado con
  `Files.GetDirectory plugin://script.skinvariables/?info=run_executebuiltin&&<ruta smb codificada>`. Kodi se cerró al
  terminar, pero el menú quedó guardado.
- Reproducción probada: "21 Grams" REMUX 1080p H.264 + DTS-HD MA 5.1 desde Samba, sin cortes.
- (antes) TMDb Helper mostraba avisos de "module could not be loaded" en Kodi 22 (Python de tvOS): esperado.

---

## Estado final (2026-11-21) — estable
- **Apple TV**: Apple TV 4K 3ª gen (AppleTV14,1), tvOS 27.3, IP 192.168.1.60. Modo desarrollador activado.
- **Kodi 21.3 estable** (oficial, `Kodi-21.3-tvos.ipa`, del .deb con SHA-256
  `0ab12ab674c931dfa14e3f50d3f31bdae13b9e191c044e40e0cf7b582bc5a5ff`). Instalado con extensiones quitadas.
- **Skin: Arctic Horizon 2** (repositorio jurialmunkey) + TMDb Helper, texturemaker, skinvariables, skinshortcuts.
  Probada en arranque en frío con la biblioteca completa: estable. Log sin errores de Python.
- **Biblioteca**: 252 películas y 90 series (1.815 episodios) desde Samba del homelab
  (`smb://192.168.1.50/Peliculas/`, `smb://192.168.1.50/Series/`). Scraper TMDb en **es-MX**, **título original**
  y carátulas. Sin traducción en TMDb queda la sinopsis original (≈25 pelis, ≈15 series).
- **Subtítulos**: a4kSubtitles 3.26.1.1 (con su repo), español → inglés. OpenSubtitles requiere cuenta propia.

## Por qué NO Kodi 22
Kodi 22 RC2 en tvOS se cerraba al arrancar en cuanto había biblioteca, con Mistuary y con Bald (también con
Helpers desactivados). Además su Python 3.14 no trae `_scproxy` (rompe urllib). Se volvió a Kodi 21.3.
Cuando salga Kodi 22 final se puede reintentar Bald/Mistuary (zips ya no están en el homelab).

## Addons parcheados (en `addons/` y en el homelab `/srv/kodi-addons`, Samba `KodiAddons`, solo lectura)
- `metadata.themoviedb.org.python-3.2.2.2-kodi.zip`: maneja respuestas gzip de TMDb + stub `_scproxy.py`.
- `metadata.tvshows.themoviedb.org.python-2.0.9.1-kodi.zip`, `service.subtitles.a4ksubtitles-3.26.1.1-kodi.zip`:
  stub `_scproxy.py`. Una actualización oficial con versión mayor los reemplaza (sin problema en Kodi 21).
- `sources.xml`: fuentes de video y de addons/logs; se copia al perfil con el Gestor de archivos.

## atvloadly (firma de Kodi)
- Docker en **Multimedia-Stack (CT103, 8 GB RAM)**: `/opt/atvloadly/compose.yaml`. Panel **http://192.168.1.50:5533**
  (sin contraseña, solo LAN).
- Renovación automática 03:00–06:00 cuando falta < 1 día (firma de 7 días). Apple TV en reposo, no desenchufado.
- Si Apple vence la sesión (error 1100 "session expired"): en Accounts → **Logout** y **Add Account** de nuevo.
- **Aviso por email**: webhook → servicio `mail-bridge` del mismo stack (`/opt/atvloadly/mail-bridge/`,
  sin puertos expuestos). Cuenta en `mail.env` (Gmail con contraseña de aplicación). Reconfigurar:
  `ssh -t multimedia sudo /opt/atvloadly/mail-bridge/configurar.sh`. Probado OK.

## Control remoto de Kodi
HTTP (8080, con tu contraseña) y "aplicaciones en otros sistemas" (9090, sin contraseña, LAN) activados para
poder configurar Kodi desde la Mac. Si no lo vas a usar: Kodi → Ajustes → Servicios → Control → apagar.
Teclado de Kodi activado en lugar del de tvOS (`input.tvosusekodikeyboard`).

## Reinstalar desde cero (si Kodi se rompe)
1. Borrar Kodi del Apple TV. 2. atvloadly → Apple TV → IPA (Remove extensions ON) → Install.
3. En Kodi activar control remoto. 4. Repetir: fuente SMB de addons, copiar `sources.xml`, instalar zips,
   Set content (es-MX + título original), escanear, repo jurialmunkey → Arctic Horizon 2.
