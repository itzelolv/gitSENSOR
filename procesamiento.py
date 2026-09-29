"""Funciones de procesamiento de las señales del WT9011DCL.

Reúne lo que se construye en 04_preprocesamiento para usarlo en los notebooks siguientes.
"""

import numpy as np
from scipy import signal

ACELERACION = ["ax", "ay", "az"]
GIROSCOPIO = ["gx", "gy", "gz"]


def agregar_magnitudes(df):
    """Agrega |a| (a_mag) y |ω| (g_mag), que no dependen de la orientación del sensor."""
    df["a_mag"] = np.sqrt((df[ACELERACION] ** 2).sum(axis=1))
    df["g_mag"] = np.sqrt((df[GIROSCOPIO] ** 2).sum(axis=1))


def recortar(df, inicio):
    """Quita los primeros `inicio` segundos y reinicia el tiempo en cero."""
    d = df[df["t"] >= inicio].reset_index(drop=True)
    d["t"] = d["t"] - d["t"].iloc[0]
    return d


def pasa_bajas(x, fc, fs, orden=4):
    """Filtro Butterworth pasa-bajas de fase cero (se aplica hacia adelante y hacia atrás)."""
    sos = signal.butter(orden, fc, btype="low", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)


def separar_gravedad(df, fs, fc=0.3):
    """Separa cada eje de aceleración en gravedad (ax_grav, ...) y aceleración del cuerpo (ax_cuerpo, ...).

    La gravedad cambia despacio, solo cuando cambia la orientación, así que se obtiene con un
    pasa-bajas de frecuencia de corte muy baja. Lo que queda es la aceleración del movimiento.
    """
    for eje in ACELERACION:
        gravedad = pasa_bajas(df[eje], fc, fs, orden=2)
        df[f"{eje}_grav"] = gravedad
        df[f"{eje}_cuerpo"] = df[eje] - gravedad
    cuerpo = [f"{eje}_cuerpo" for eje in ACELERACION]
    df["cuerpo_mag"] = np.sqrt((df[cuerpo] ** 2).sum(axis=1))


def preprocesar(df, fs, recorte=1.0, fc=10.0, fc_gravedad=0.3):
    """Recorta el inicio, filtra aceleración y giroscopio, separa la gravedad y agrega las magnitudes.

    Los ángulos no se filtran: yaw salta de 180° a -180° y un filtro lo deformaría en ese salto.
    """
    d = recortar(df, recorte)
    for columna in ACELERACION + GIROSCOPIO:
        d[columna] = pasa_bajas(d[columna], fc, fs)
    separar_gravedad(d, fs, fc_gravedad)
    agregar_magnitudes(d)
    return d
