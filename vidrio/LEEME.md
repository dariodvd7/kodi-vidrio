# Vidrio: skin estilo Apple TV para Kodi

Inicio al estilo de la app TV del Apple TV, pensado para Kodi 22 **sin biblioteca** en el Apple TV (también anda en
Kodi 21 de la Mac).

- **Héroe arriba**: fanart del título con foco, etiqueta (PELÍCULA/SERIE y puntaje), título, año · géneros · duración ·
  clasificación, sinopsis en español y botón Ver/Episodios. El borde de abajo se difumina hacia el fondo.
- **Tráiler de fondo**: si el foco queda 3 segundos sobre un título, el servicio de `plugin.video.vidrio` reproduce el
  tráiler de YouTube en modo ventana y la skin lo muestra en el héroe. Se corta al mover el foco o salir del inicio.
- **Barra de vidrio** arriba: Inicio, Películas, Series, Géneros, Buscar, Archivos, Ajustes, Salir.
- **Control**: ▲▼ entre filas y hasta la barra; ◀▶ entre pestañas. Atrás en una fila sube a la barra; Atrás en la
  barra cierra Kodi. El vidrio es simulado
  (Kodi no tiene desenfoque en tiempo real): panel traslúcido con brillo y filete claro.
- **Filas**: Agregadas recientemente, Películas, Series, Acción, Comedia, Drama, Suspenso, Ciencia ficción. Tarjetas
  apaisadas con esquinas redondeadas; la enfocada crece y muestra el título.
- **Ficha** (`DialogVideoInfo.xml` propia): tapa el inicio, fanart difuminado, título, datos, lema y sinopsis en
  español, panel de vidrio con título original, género, duración, clasificación y estudio, y botones de vidrio
  Reproducir / Reanudar / Ver tráiler. Las películas y episodios se reproducen a través del add-on
  (`?reproducir=`), así Kodi no reemplaza los datos con los del scraper de la carpeta (en inglés).
- **Pantalla de Películas / Series** (`Custom_1151_VidrioGrilla.xml`, ventana 1151, pestañas de la barra):
  encabezado con el título enfocado (fanart difuminado, datos, sinopsis), píldoras de orden (A-Z, Recientes, Año,
  Puntaje: `?orden=`) y grilla de pósters con esquinas redondeadas. Una película abre la ficha; una serie, su pantalla.
- **Géneros** (`Custom_1153_VidrioGeneros.xml`, ventana 1153): tarjetas de vidrio con el fondo del título mejor
  puntuado de cada género (uno distinto por género), nombre y cantidad; los más grandes primero. Abre la grilla 1151
  con `Vidrio.GrillaQ=genero=…` y `Vidrio.GrillaTitulo`.
- **Ventanas internas de Kodi en vidrio** (diálogos, ajustes de subtítulos/audio, menús, listas, teclado, ajustes de
  add-ons, páginas de configuración): `herramientas/vidrio_global.py` reemplaza en los XML de Estuary los fondos de
  diálogo, barras de foco y botones por `glass_dialog`, `glass_focus` y `glass_nofo`, y ajusta `colors/defaults.xml`
  (foco blanco, fondos oscuros). El fondo común de diálogos (`DialogBackgroundCommons` en `Includes.xml`), el menú
  contextual y el teclado se cambiaron a mano: panel de vidrio, sin franja de encabezado ni logo, fondo más oscuro.
- **Búsqueda** (`Custom_1152_VidrioBuscar.xml`, ventana 1152, pestaña Buscar): campo de vidrio; vacío muestra lo agregado
  últimamente; con texto busca películas y series sin acentos ni mayúsculas, por título, título original y género
  (`?buscar=1&ventana=1&texto=`), ordenado por cuánto coincide.
- **Pantalla de serie** (`Custom_1150_VidrioSerie.xml`, ventana 1150): encabezado con fanart difuminado, título, datos y
  sinopsis; temporadas como píldoras de vidrio y episodios como tarjetas de vidrio con la captura del episodio (Jellyfin la sirve
  achicada a 640 px en `http://192.168.1.50:8097/Items/<id>/Images/Primary`, sin sesión), número, título, duración y
  sinopsis. Se abre desde el inicio, la pestaña Series y Buscar (`?abrir_serie=`). Elegir un episodio lo reproduce.
  El catálogo usa el texto después de `S01E05` del nombre del archivo, o "Episodio N", cuando Jellyfin no tiene título
  del episodio, el título original de Sonarr cuando TMDb no tiene título en español (Jellyfin deja "Episodio N"; quedan
  95 de 1823 sin título), y los datos de Radarr cuando Jellyfin no identificó una película.
- **Reproductor** (`VideoOSD.xml` propia): panel de vidrio con título, barra de avance, tiempo, "Termina a las", tiempo
  restante, audio y subtítulos en uso, y botones Pausa/Reproducir, −10 s, +10 s, **Subtítulos** (osdsubtitlesettings),
  **Audio** (osdaudiosettings), **Buscar subtítulos** (a4kSubtitles), Siguiente, Más y Detener. La barra de Estuary de
  arriba y la de avance se ocultan mientras están los controles.
- **Ajustes** (`Settings.xml` propia): tarjetas de vidrio en tres secciones: Vidrio (tráileres y subtítulos, proveedores
  de subtítulos, actualizar catálogo, YouTube), Kodi y Herramientas.
- **Subtítulos en español**: el servicio deja español como idioma preferido y a4kSubtitles con búsqueda y descarga
  automática. Si el video trae subtítulos en español, se usan; si no, a4kSubtitles los busca y baja solo.

## Piezas
| Carpeta | Qué es |
|---|---|
| `skin.vidrio/` | La skin: copia de Estuary 21 (GPL-2 / CC BY-SA 4.0) con `Home.xml` nuevo, `Includes_Vidrio.xml` y texturas en `media/vidrio/`. El resto de las ventanas (ficha, reproductor, ajustes) son las de Estuary. Pide `xbmc.gui` 5.17.0: sirve para Kodi 21 y 22. |
| `plugin.video.vidrio/` | Add-on: listados con datos completos (`?lista=peliculas|series|recientes|generos`, `?genero=`, `?serie=`, `?buscar=1`) y servicio (tráiler de fondo y subtítulos). |
| `homelab/catalogo.py` | Arma `/srv/kodi-addons/vidrio/catalogo.json` (Samba `KodiAddons`) con textos en español de Jellyfin (es-419), tráileres de Radarr y Jellyfin, y duración de Radarr/Sonarr. Instalado en `/opt/kodi-artwork/`, corre a diario a las 04:15 después de `caratulas.py`. |
| `herramientas/` | `texturas.py` (genera las texturas), `includes.py` (genera `Includes_Vidrio.xml`; no editar ese archivo a mano), Home original de Estuary. |
| `dist/` | Zips e IPA armados (fuera de git; `herramientas/zips.py`, `fork/armar_ipa.py`; publicados en Releases). |

## Red de casa (`local.json`)
En el repositorio la IP del homelab es la de ejemplo, `192.168.1.50`. La real va en `vidrio/local.json` (fuera de git;
copiar `local.ejemplo.json`): `herramientas/zips.py` y `fork/armar_ipa.py` la ponen en el catálogo del plugin al
empaquetar (con `--generico`, la de ejemplo). En el homelab, `catalogo.py` la toma de la variable `VIDRIO_HOMELAB`
(sin ella usa la de ejemplo): en el cron, `VIDRIO_HOMELAB=<ip> /opt/kodi-artwork/catalogo.py`.

## Instalar
1. En Kodi: Add-ons → Instalar desde un archivo zip → `smb://192.168.1.50/KodiAddons/` → `plugin.video.vidrio-1.2.5.zip`,
   después `skin.vidrio-1.2.0.zip` (versiones actuales: add-on 1.2.5, skin 1.2.0). La skin pide el add-on, por eso va
   primero.
2. Para tráileres: instalar YouTube (`plugin.video.youtube`) del repositorio oficial. Funciona sin clave propia de la API.
3. Interfaz → Skin → Vidrio.

## YouTube en macOS/tvOS (parche)
El add-on de YouTube sirve el manifiesto del tráiler desde un servidor local. En macOS y tvOS su función
`get_connect_address` falla (conectar un socket UDP al puerto 0 da Errno 49) y usa `xbmc.getIPAddress()`, que en el
Apple TV devolvía 10.207.65.146, una IP que no conecta: error "Cannot download the stream manifest file". El servicio de
Vidrio agrega al final de `plugin.video.youtube/.../kodion/network/http_server.py` una versión de esa función que usa
127.0.0.1 cuando el servidor escucha ahí, pone `kodion.http.listen` en 127.0.0.1 y reinicia el add-on de YouTube. Lo
revisa cada ~5 minutos, así que se vuelve a aplicar si YouTube se actualiza y pisa el archivo. Se puede desactivar
apagando "Reproducir el tráiler de fondo" en los ajustes de Vidrio.

Si los tráileres fallan dos veces seguidas, el servicio no los vuelve a intentar hasta reiniciar Kodi (cada fallo
muestra un cartel de error).

**Tubed** (`plugin.video.tubed` 2.0.0, el "Tube" del repositorio oficial) quedó instalado en el Apple TV, pero no sirve:
su código para obtener el video es de 2021 y YouTube ya no le responde (`ContentNoResponse`).

## Trakt (seguimiento de lo que se ve)
- Add-on oficial **Trakt** (`script.trakt` 3.9.0, repositorio de Kodi). Identifica lo reproducido fuera de la biblioteca
  con la propiedad `Window(home).script.trakt.ids`: el add-on Vidrio la pone al reproducir (`?reproducir=`) con los
  códigos de la película (TMDb, IMDb) o de la serie (TVDB, TMDb, IMDb); temporada y episodio salen del reproductor.
  Los códigos vienen del catálogo (Radarr/Sonarr, y Jellyfin si faltan): 252/252 películas, 90/91 series.
- El servicio de Vidrio deja Trakt con **Excluir HTTP** activado (los tráileres de YouTube llegan por http y no deben
  contar) y **Excluir plugins** desactivado.
- **Continuar viendo** (fila 5100, la primera del inicio) y pestaña **Trakt** (grilla 1151 con `lista=trakt`): salen de
  Trakt (`/sync/playback` y `/sync/watchlist`) con el token y el cliente de script.trakt (`resources/lib/trakt.py`, sin
  otra vinculación), cruzados con el catálogo por TMDb/IMDb/TVDB. Elegir uno reproduce con `?reproducir=…&desde=<%>`
  (propiedad `StartPercent`): retoma donde quedó. La tarjeta muestra la barra de progreso y "Te quedan …". Las
  respuestas se guardan 1 min (lista: 10 min); al cortar algo que no sea un tráiler, el servicio borra esa caché a los
  8 s y cambia `Window(home).Property(Vidrio.Trakt)`, que va en la ruta de la fila: la skin la recarga. La fila se
  oculta si no hay nada, y la navegación la saltea. `PlayMedia` desde el inicio deja el video detrás del inicio (se
  oye pero no se ve): el servicio pasa a pantalla completa, una sola vez, cada video del usuario que arranca con el
  inicio en pantalla. El plugin trae su propio `_scproxy.py` para que `urllib` ande en
  el Apple TV.
- Vincular la cuenta: Ajustes de Trakt → Autorizar (o `RunScript(script.trakt,action=auth_info)`), y en
  https://auth.trakt.tv/activate ingresar el código que muestra Kodi.
- Mac y Apple TV: instalado, vinculado y probado (22/11: "21 gramos" llega con sus códigos y el corte pasado el 1 %).
- En el Apple TV el Python de Kodi 22 RC2 no trae `_scproxy` y `urllib.request` lo importa: el servicio de Trakt no
  arranca ("No module named '_scproxy'"). `script.module.dateutil-2.8.2.1-kodi.zip` (en `KodiAddons` y `dist/`) es el
  dateutil 2.8.2 con un `_scproxy.py` mínimo; Trakt depende de dateutil, así que lo encuentra. `requests` 2.31.0.1 trae
  el mismo arreglo para YouTube.

## Apple TV: ajustes que no hay que cambiar
El 22/11 Kodi en el Apple TV se cerraba a los 2-3 segundos de abrir, con el inicio ya dibujado y sin error en el log.
Se arregló reinstalando Kodi limpio con atvloadly (borrar la app en el Apple TV y `POST /api/apps/1/reinstall`). Los
datos viejos tenían la interfaz en 3840x2160 a 23,98 Hz, y Kodi usaba el teclado de tvOS: abrirlo cerraba Kodi. En la
instalación nueva quedaron:
- `input.tvosusekodikeyboard` = activado (teclado de Kodi, no el de tvOS).
- `videoplayer.adjustrefreshrate` = 0 (no cambia la frecuencia al reproducir) y `videoscreen.screenmode` = DESKTOP.
- Idioma `resource.language.es_ar`, país Argentina, subtítulos en español.
- En el Apple TV: Ajustes → Video y audio → Ajustar contenido desactivado.
Kodi guarda los ajustes al salir: si se cierra solo, los cambios hechos por JSON-RPC en esa sesión se pierden.
Las imágenes de las carpetas de películas se achicaron (carátula 1000x1500, fondo 1920x1080); `caratulas.py` copia
las nuevas a tamaño completo.

## Kodi Vidrio (IPA con todo adentro)
`fork/armar_ipa.py` arma `dist/Kodi-Vidrio-22.0rc2.ipa` a partir del IPA oficial (`../Kodi-22.0rc2-tvos.ipa`), sin
recompilar Kodi:
- Se llama **Kodi Vidrio** y su identificador es `org.xbmc.kodi-tvos.vidrio`: se instala al lado del Kodi oficial, con
  sus propios datos.
- Trae adentro (en `addon-manifest.xml` como opcionales, así arrancan activos) la skin y el plugin Vidrio de este
  repositorio, YouTube (con el parche de conexión local ya aplicado), Trakt y su botón de lista, el español de
  Argentina y sus dependencias, bajados del repositorio oficial de Kodi 22 ("piers"), y a4kSubtitles con su
  repositorio (`fork/extra/`).
- Valores de fábrica: skin Vidrio, `es_ar`, Argentina, subtítulos en español, teclado de Kodi, sin cambio de
  frecuencia, orígenes desconocidos y control remoto (JSON-RPC 9090) activados.
- `_scproxy.py` en el Python de la app: ya no hacen falta los requests/dateutil parcheados.
- Trakt no viene vinculado (es de cada cuenta): la primera vez muestra el código para https://auth.trakt.tv/activate.

Rearmar (otra versión de Vidrio o de Kodi: `--ipa` y `--salida`): `python3 fork/armar_ipa.py`. Instalar con
atvloadly: página del Apple TV → IPA URL (servir el archivo un rato con `python3 -m http.server` en el Mac) o IPA
file, la cuenta, "Remove extensions" activado. Instalado y probado el 22/11 (arranca con todo puesto, sin errores).
Reinstalar encima conserva los ajustes de Kodi (están en NSUserDefaults) pero borra los datos de los add-ons
(`Library/Caches`): hay que volver a vincular Trakt. El servicio recarga "Continuar viendo" solo al vincularlo (y
otra vez a los 70 s: recién vinculada, Trakt puede responder la lista vacía). Para actualizar solo Vidrio sin perder
Trakt: agregar `smb://<homelab>/KodiAddons/` como fuente e instalar `plugin.video.vidrio-<versión>.zip` encima.

## Android TV (TCL)
Kodi 21.2 en un TCL Smart TV Pro (Android TV 11): solo la skin y el plugin, sin IPA. Pasos: activar el control remoto
(`services.esallinterfaces`) y los orígenes desconocidos, agregar `smb://<homelab>/KodiAddons/` como fuente, instalar
`plugin.video.vidrio` y `skin.vidrio` desde zip, el español (Argentina), YouTube y Trakt del repositorio oficial y
a4kSubtitles (repositorio y add-on) desde zip; país Argentina, subtítulos en español, sin cambio de frecuencia; skin
Vidrio y vincular Trakt. En Android no hacen falta `_scproxy` ni el teclado de tvOS; el parche de YouTube no molesta.

## Probado
- Mac, Kodi 21.3: inicio, filas, datos en español, navegación con flechas, tráiler de YouTube de fondo con el
  difuminado; se corta al mover el foco.
- Apple TV, Kodi 22 RC2: navegación con flechas (filas ↔ barra de arriba ↔ pestañas) y tráiler de YouTube de fondo
  ("21 gramos", empieza en 480p).
- Diagnóstico: `plugin://plugin.video.vidrio/?log=kodi.log` (o `kodi.old.log`, con `desde=` y `cuantas=`) devuelve las
  líneas del log como listado, para leerlo por JSON-RPC con `Files.GetDirectory`. `?copiar_log=1` lo copia a
  `smb://192.168.1.50/KodiLogs/` (ese recurso se crea solo cuando hace falta y se borra después).

## Análisis de Kodi para tvOS
`../analisis/COMO-ESTA-HECHO.md`.
