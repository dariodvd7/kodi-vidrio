# Cómo está hecho Kodi para Apple TV (22.0 RC2)

Analizado con REA (inspect_macho, inspect_plist) y con las herramientas de Xcode (`otool`, `nm`, `codesign`) sobre
`Kodi-22.0rc2-tvos.ipa`, sin ejecutarlo. REA no tenía un descompilador configurado (Ghidra/Hopper/IDA), así que no hay
pseudocódigo, solo estructura.

## El paquete
- `Kodi.app`, bundle `org.xbmc.kodi-tvos`, versión 22.0-RC2 (build 20261109-d686683a55), compilado con Xcode 26.3
  contra el SDK tvOS 26.2, mínimo tvOS 12. Solo Apple TV (`UIDeviceFamily` 3), arm64 y OpenGL ES 3.
- Sin firma de equipo (`TeamIdentifier=not set`): por eso se firma con la cuenta propia (atvloadly) cada 7 días.
- `NSAllowsArbitraryLoads`: deja usar http sin cifrar (Samba, servidores locales).
- Esquema `kodi://` y una extensión **Top Shelf** (`kodi-topshelf.appex`, `com.apple.tv-services`): la fila que se ve
  arriba en la pantalla de inicio del Apple TV.

## El ejecutable (97 MB, Mach-O arm64)
- Un solo binario con todo el núcleo en C++: reproductor, GUI, base de datos, red, JSON-RPC.
- Usa los frameworks de Apple: VideoToolbox y AVFoundation (decodificación por hardware), CoreAudio/AudioToolbox,
  UIKit, **GameController** (el control Siri: `GCMicroGamepad`, eventos "Siri remote select long press"), MediaPlayer
  (Centro de control), OpenGLES (dibuja la interfaz).
- **Python 3.14 enlazado estáticamente**: 87 módulos nativos (`PyInit__ssl`, `_socket`, `_sqlite3`, `_ctypes`…) van
  dentro del binario y `lib/python3.14/lib-dynload` está vacío. No incluye `_scproxy` (es de macOS), por eso fallaba
  `urllib` y hubo que poner el stub `_scproxy.py` en los add-ons.

## Lo que no es el ejecutable
- `Frameworks/` (116 MB, 111 entradas): los add-ons binarios como frameworks: decodificadores de audio,
  `inputstream.adaptive` (streaming/DRM), clientes PVR, emuladores libretro, joystick. tvOS no deja cargar código
  bajado de internet, así que **los add-ons binarios solo pueden venir dentro de la IPA**.
- `AppData/AppHome/` (260 MB): lo mismo que la carpeta de Kodi en cualquier sistema: `addons/` (158, entre ellos
  **skin.estuary**), `system/`, `media/`, `userdata/`.
- `lib/python3.14/` (38 MB): la biblioteca estándar de Python en `.py`.

## Lo que importa para la skin
- `xbmc.gui` **5.18.0** con compatibilidad hacia atrás hasta **5.17.0**: una skin que pida 5.17.0 funciona en Kodi 21
  (Mac) y en Kodi 22 (Apple TV).
- Las skins son solo XML e imágenes (no código nativo), así que se pueden instalar en el Apple TV desde un zip sin
  tocar la IPA.
