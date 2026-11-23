# -*- coding: utf-8 -*-
"""Abrir otra app en tvOS desde Kodi (por ejemplo DGO desde la guía).

Kodi para tvOS no tiene un comando para abrir otra app, pero su Python trae ctypes: con el runtime de Objective-C se
llama a [[UIApplication sharedApplication] openURL:options:completionHandler:] en el hilo principal (UIKit lo exige),
con dispatch_async_f sobre la cola principal. Devuelve True si se pudo pedir; si la app no existe, tvOS no hace nada.
"""
import ctypes
import threading

_OBJC = '/usr/lib/libobjc.A.dylib'
_SISTEMA = '/usr/lib/libSystem.B.dylib'
_vivos = []  # callbacks de ctypes: tienen que seguir vivos hasta que corran en el hilo principal


def _runtime():
    objc = ctypes.CDLL(_OBJC)
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    envio = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
    return objc, envio


def abrir_url(url, espera=3.0):
    objc, envio = _runtime()
    clase, sel = objc.objc_getClass, objc.sel_registerName

    def msg(restype, *argtypes):
        return ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes)(envio)

    texto = msg(ctypes.c_void_p, ctypes.c_char_p)(clase(b'NSString'), sel(b'stringWithUTF8String:'), url.encode('utf-8'))
    nsurl = msg(ctypes.c_void_p, ctypes.c_void_p)(clase(b'NSURL'), sel(b'URLWithString:'), texto)
    if not nsurl:
        return False
    app = msg(ctypes.c_void_p)(clase(b'UIApplication'), sel(b'sharedApplication'))
    opciones = msg(ctypes.c_void_p)(clase(b'NSDictionary'), sel(b'dictionary'))
    abrir = msg(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
    listo = threading.Event()

    @ctypes.CFUNCTYPE(None, ctypes.c_void_p)
    def en_hilo_principal(_contexto):
        try:
            abrir(app, sel(b'openURL:options:completionHandler:'), nsurl, opciones, None)
        finally:
            listo.set()

    _vivos.append(en_hilo_principal)
    sistema = ctypes.CDLL(_SISTEMA)
    cola_principal = ctypes.c_void_p.in_dll(sistema, '_dispatch_main_q')
    sistema.dispatch_async_f.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    sistema.dispatch_async_f(ctypes.addressof(cola_principal), None,
                             ctypes.cast(en_hilo_principal, ctypes.c_void_p))
    return listo.wait(espera)
