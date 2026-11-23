# -*- coding: utf-8 -*-
"""Abrir otra app en tvOS desde Kodi (por ejemplo DGO desde la guía).

Kodi para tvOS no tiene un comando para abrir otra app, pero su Python trae ctypes: con el runtime de Objective-C se
llama a [[UIApplication sharedApplication] openURL:options:completionHandler:] en el hilo principal (UIKit lo exige),
con dispatch_async_f sobre la cola principal. El resultado llega por un block de Objective-C armado a mano (ABI de
blocks: isa, flags, reserved, invoke, descriptor), así se sabe si tvOS abrió la app.
"""
import ctypes
import threading

import xbmc

_OBJC = '/usr/lib/libobjc.A.dylib'
_SISTEMA = '/usr/lib/libSystem.B.dylib'
_vivos = []  # callbacks y blocks: tienen que seguir vivos hasta que tvOS los llame
BLOCK_IS_GLOBAL = 1 << 28


def log(msg):
    xbmc.log(f'[vidrio] abrir: {msg}', xbmc.LOGINFO)


class _Descriptor(ctypes.Structure):
    _fields_ = [('reserved', ctypes.c_ulong), ('size', ctypes.c_ulong)]


_INVOCAR = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_bool)


class _Block(ctypes.Structure):
    _fields_ = [('isa', ctypes.c_void_p), ('flags', ctypes.c_int), ('reserved', ctypes.c_int),
                ('invoke', _INVOCAR), ('descriptor', ctypes.POINTER(_Descriptor))]


def abrir_url(url, espera=8.0):
    """Devuelve (corrió en el hilo principal, tvOS respondió, la app se abrió)."""
    objc = ctypes.CDLL(_OBJC)
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    envio = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
    clase, sel = objc.objc_getClass, objc.sel_registerName

    def msg(restype, *argtypes):
        return ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes)(envio)

    texto = msg(ctypes.c_void_p, ctypes.c_char_p)(clase(b'NSString'), sel(b'stringWithUTF8String:'), url.encode('utf-8'))
    nsurl = msg(ctypes.c_void_p, ctypes.c_void_p)(clase(b'NSURL'), sel(b'URLWithString:'), texto)
    if not nsurl:
        log(f'{url}: no es un enlace válido')
        return False, False, False
    app = msg(ctypes.c_void_p)(clase(b'UIApplication'), sel(b'sharedApplication'))
    opciones = msg(ctypes.c_void_p)(clase(b'NSDictionary'), sel(b'dictionary'))
    abrir = msg(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
    estado = {'corrio': False, 'respondio': False, 'abrio': False}
    listo = threading.Event()
    sistema = ctypes.CDLL(_SISTEMA)

    def al_terminar(_block, exito):
        estado['respondio'], estado['abrio'] = True, bool(exito)
        listo.set()

    invocar = _INVOCAR(al_terminar)
    descriptor = _Descriptor(0, ctypes.sizeof(_Block))
    isa = ctypes.addressof(ctypes.c_void_p.in_dll(sistema, '_NSConcreteGlobalBlock'))
    block = _Block(isa, BLOCK_IS_GLOBAL, 0, invocar, ctypes.pointer(descriptor))

    @ctypes.CFUNCTYPE(None, ctypes.c_void_p)
    def en_hilo_principal(_contexto):
        estado['corrio'] = True
        abrir(app, sel(b'openURL:options:completionHandler:'), nsurl, opciones, ctypes.addressof(block))

    _vivos.extend([invocar, descriptor, block, en_hilo_principal])
    cola_principal = ctypes.c_void_p.in_dll(sistema, '_dispatch_main_q')
    sistema.dispatch_async_f.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    sistema.dispatch_async_f(ctypes.addressof(cola_principal), None, ctypes.cast(en_hilo_principal, ctypes.c_void_p))
    listo.wait(espera)
    log(f"{url}: hilo principal {'sí' if estado['corrio'] else 'no'}, respuesta de tvOS "
        f"{'sí' if estado['respondio'] else 'no'}, abrió {'sí' if estado['abrio'] else 'no'}")
    return estado['corrio'], estado['respondio'], estado['abrio']
