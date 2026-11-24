# Instalar Kodi Vidrio

Kodi Vidrio es una skin y un add-on para Kodi con la interfaz de la app TV del Apple TV: tráiler de fondo, datos y
sinopsis en español, "Continuar viendo" con Trakt, subtítulos en español automáticos, guía de TV de Argentina y
partidos en vivo y próximos (Primera División, Copa Argentina, Libertadores, Sudamericana y NFL).

Anda en **Apple TV** (Kodi 22, con el IPA de este repositorio), **Android TV / Google TV** (Kodi 21 o 22) y **Mac,
Windows o Linux** (Kodi 21 o 22).

> **Antes de empezar:** Vidrio no usa la biblioteca de Kodi. Las películas y series salen de un catálogo
> (`catalogo.json`) que arma un servidor de tu casa (homelab) a partir de **Jellyfin, Radarr y Sonarr**. Sin ese
> catálogo, la skin se instala y se ve, pero las filas de películas y series quedan vacías. La parte 1 explica cómo
> armarlo.

## Qué hace falta

| Para | Hace falta |
|---|---|
| Películas y series | Un servidor Linux con Jellyfin, Radarr y Sonarr (en Docker), las películas y series compartidas por Samba, y Python 3. Seerr es opcional: aporta sinopsis en español que Jellyfin no tiene. |
| Tráileres | El add-on YouTube del repositorio oficial de Kodi (viene adentro del IPA). |
| "Continuar viendo" y la lista de Trakt | Una cuenta de [Trakt](https://trakt.tv) (gratis) y el add-on Trakt (viene adentro del IPA). |
| Guía de TV y partidos | Nada más que el servidor: la guía usa XMLTV públicos de Argentina y los partidos, el marcador público de ESPN. Abrir los canales en DGO funciona solo en Android TV, con la app de DGO instalada. |
| Apple TV | Una Mac o un servidor con [atvloadly](https://github.com/bitxeno/atvloadly) (u otra forma de instalar IPA) y una cuenta de Apple. |

## Parte 1: el servidor (homelab)

Los scripts están en [`vidrio/homelab/`](vidrio/homelab/). Están hechos para un homelab concreto: antes de correrlos,
revisá las constantes del principio de cada archivo y cambialas por las tuyas.

1. **Carpeta compartida.** Creá `/srv/kodi-addons/vidrio/` y compartí `/srv/kodi-addons` por Samba con el nombre
   `KodiAddons`, de solo lectura y para tu red. Ahí van `catalogo.json`, `guia.json` y `partidos.json`. Compartí
   también las películas y las series (en el código se llaman `Peliculas` y `Series`).
2. **Copiá los scripts** a `/opt/kodi-artwork/` (`catalogo.py`, `caratulas.py`, `guia.py`, `partidos.py`,
   `sinopsis_es.json` y `canales_dgo.json`).
3. **Ajustá `catalogo.py`:**
   - `JF_DB`: la base de Jellyfin (`jellyfin.db`).
   - `RAIZ`: cómo ve Jellyfin las carpetas (`/movies/`, `/tv/`), dónde están en el servidor y cómo se llaman en Samba.
   - `arr()`: la carpeta donde Radarr y Sonarr guardan su `config.xml` (de ahí toma las claves de la API) y sus
     puertos (7878 y 8989).
   - `SEERR` (opcional): el `settings.json` de Seerr.
   - La IP del servidor va en la variable `VIDRIO_HOMELAB`, no en el código.
4. **Probalo a mano:**
   ```bash
   sudo /opt/kodi-artwork/caratulas.py
   ```
   ```bash
   sudo VIDRIO_HOMELAB=<ip del servidor> /opt/kodi-artwork/catalogo.py
   ```
   ```bash
   sudo /opt/kodi-artwork/guia.py
   ```
   ```bash
   sudo /opt/kodi-artwork/partidos.py --mostrar
   ```
   `caratulas.py` copia a cada carpeta el póster y el fondo (`folder.jpg`, `fanart.jpg`) que Radarr y Sonarr ya
   tienen. `catalogo.py` termina diciendo cuántas películas y series encontró.
5. **Programalos con cron** (`/etc/cron.d/vidrio`):
   ```
   0 4 * * *    root /opt/kodi-artwork/caratulas.py > /var/log/kodi-caratulas.log 2>&1
   15 4 * * *   root VIDRIO_HOMELAB=<ip> /opt/kodi-artwork/catalogo.py > /var/log/kodi-catalogo.log 2>&1
   10 */3 * * * root /opt/kodi-artwork/guia.py > /var/log/kodi-guia.log 2>&1
   */2 * * * *  root /usr/bin/python3 /opt/kodi-artwork/partidos.py > /var/log/kodi-partidos.log 2>&1
   ```

**Sin Jellyfin, Radarr y Sonarr** se puede escribir `catalogo.json` con otra herramienta. Formato mínimo:

```json
{
  "version": 1,
  "generado": 1795500000,
  "peliculas": [
    {"titulo": "Nueve reinas", "anio": 2000, "generos": ["Crimen", "Drama"], "sinopsis": "…",
     "puntaje": 7.9, "minutos": 114, "agregada": 1795400000, "trailer": "<id de YouTube>",
     "carpeta": "Nueve reinas (2000)",
     "dir": "smb://192.168.1.50/Peliculas/Nueve reinas (2000)/",
     "archivo": "smb://192.168.1.50/Peliculas/Nueve reinas (2000)/Nueve reinas (2000).mkv"}
  ],
  "series": []
}
```

El fondo y el póster se leen de `fanart.jpg` y `folder.jpg` dentro de `dir`. Para ver todos los campos (series con
temporadas y episodios incluidas), mirá `catalogo.py`.

**Opcional: actualizaciones automáticas.** [`vidrio/homelab/kodi-repo/`](vidrio/homelab/kodi-repo/) es un nginx que
sirve un repositorio de add-ons propio. `vidrio/herramientas/repo.py --subir` lo arma y lo sube. Con el repositorio
instalado, cada versión nueva llega sola a todos los Kodi de la casa.

## Parte 2: Apple TV

1. Bajá `Kodi-Vidrio-22.0rc2.ipa` del [último release](https://github.com/dariodvd7/kodi-vidrio/releases/latest).
2. En atvloadly: tu Apple TV → "IPA file" → el IPA → elegí tu cuenta de Apple → activá **"Remove extensions
   (Plug-ins)"** → Install. atvloadly lo firma: con una cuenta gratis hay que renovarlo cada 7 días, y atvloadly
   puede hacerlo solo.
3. Abrí **Kodi Vidrio**. Se instala al lado del Kodi oficial, sin reemplazarlo, y ya trae la skin, el add-on,
   YouTube, Trakt, a4kSubtitles y el español de Argentina.
4. Ajustes → Vidrio → **Tráileres y subtítulos** → **Archivo de catálogo**: cambiá `192.168.1.50` por la IP de tu
   servidor (`smb://<ip>/KodiAddons/vidrio/catalogo.json`). La guía y los partidos se buscan en la misma carpeta.
5. Vinculá Trakt: Kodi muestra un código. Ingresalo en https://auth.trakt.tv/activate.

Para pasar a una versión nueva sin perder la vinculación de Trakt, no reinstales el IPA: instalá los zips del
release encima, como en la parte 3.

## Parte 3: Android TV, Mac, Windows o Linux

1. Instalá Kodi 21 o 22 desde la tienda de tu equipo o desde [kodi.tv](https://kodi.tv/download).
2. Ajustes → Sistema → Add-ons → activá **Orígenes desconocidos**.
3. Bajá del [último release](https://github.com/dariodvd7/kodi-vidrio/releases/latest)
   `plugin.video.vidrio-<versión>.zip` y `skin.vidrio-<versión>.zip`, y copialos a una carpeta que Kodi vea (un
   pendrive, la carpeta compartida del servidor, Descargas).
4. Add-ons → Instalar desde un archivo .zip → primero el **plugin**, después la **skin**. La skin necesita el plugin.
   Cuando Kodi pregunte si querés usar la skin nueva, decí que sí (o Ajustes → Interfaz → Skin → Vidrio).
5. Desde el repositorio oficial de Kodi, instalá **YouTube** (tráileres), **Trakt** (opcional) y **a4kSubtitles**
   (opcional, subtítulos en español automáticos).
6. Ajustes → Vidrio → **Tráileres y subtítulos** → **Archivo de catálogo**: la IP de tu servidor, como en el paso 4
   de la parte 2.

En Android TV, la pestaña **DGO** muestra la guía y abre los canales en la app de DGO. DGO no abre si la
**depuración USB** está activada en el televisor: apagala en Opciones de desarrollador.

## Si algo no anda

| Pasa esto | Probá esto |
|---|---|
| Las filas de películas y series están vacías | Revisá el archivo de catálogo en los ajustes de Vidrio y abrí esa ruta desde Kodi (Archivos), para ver que llegue a la carpeta compartida. |
| No hay tráileres | Instalá YouTube del repositorio oficial. Si fallan seguido, apagalos en los ajustes de Vidrio. |
| La guía o los partidos no aparecen | Fijate que `guia.json` y `partidos.json` estén al lado de `catalogo.py`. "Deportes en vivo" solo se ve mientras se juega un partido. |
| Kodi pide desinstalar Vidrio para actualizarlo | Ajustes → Sistema → Add-ons → Actualizaciones → "Cualquier repositorio". |
| DGO muestra "modo depuración USB activado" | Apagá la depuración USB en el televisor y volvé a abrir DGO. |

Los detalles de cómo está hecho cada parte están en [`vidrio/LEEME.md`](vidrio/LEEME.md). Si encontrás un problema,
abrí un issue en este repositorio.
