"""Comunicación con el sensor WT9011DCL por Bluetooth Low Energy.

Reúne las funciones construidas paso a paso en 01_conexion (separar paquetes,
decodificarlos, leer registros) y agrega la configuración de la frecuencia de
muestreo, la grabación de señales y el guardado en CSV.
"""

import asyncio
import struct
import time
from pathlib import Path

import numpy as np
import pandas as pd
from bleak import BleakClient

UUID_DATOS = "0000ffe4-0000-1000-8000-00805f9a34fb"      # el sensor envía (notify)
UUID_COMANDOS = "0000ffe9-0000-1000-8000-00805f9a34fb"   # el sensor recibe (write)

NOMBRES = ["ax", "ay", "az", "gx", "gy", "gz", "roll", "pitch", "yaw"]
ESCALAS = [16] * 3 + [2000] * 3 + [180] * 3

REG_FRECUENCIA = 0x03
REG_TEMPERATURA = 0x40
REG_BATERIA = 0x64

# Valor que se escribe en el registro 0x03 para cada frecuencia de muestreo [Hz]
FRECUENCIAS = {10: 0x06, 20: 0x07, 50: 0x08, 100: 0x09}


def separar_paquetes(buffer):
    """Extrae del buffer los paquetes completos de 20 bytes. Los bytes sobrantes se quedan en el buffer."""
    paquetes = []
    while len(buffer) >= 20:
        if buffer[0] == 0x55 and buffer[1] in (0x61, 0x71):
            paquetes.append(bytes(buffer[:20]))
            del buffer[:20]
        else:
            del buffer[0]
    return paquetes


def decodificar(paquete):
    """Convierte un paquete 0x61 en un diccionario con aceleración [g], velocidad angular [°/s] y ángulos [°]."""
    enteros = struct.unpack("<9h", paquete[2:20])
    return {n: v / 32768 * e for n, v, e in zip(NOMBRES, enteros, ESCALAS)}


def porcentaje_bateria(voltaje):
    """Carga aproximada de la batería según la tabla del fabricante."""
    tabla = [(3.96, 100), (3.93, 90), (3.87, 75), (3.82, 60), (3.79, 50), (3.77, 40),
             (3.73, 30), (3.70, 20), (3.68, 15), (3.50, 10), (3.40, 5)]
    for umbral, porcentaje in tabla:
        if voltaje > umbral:
            return porcentaje
    return 0


def agregar_tiempo(df):
    """Agrega la columna t, un eje de tiempo uniforme, y regresa la frecuencia de muestreo estimada.

    El sensor mide a intervalos regulares, pero los paquetes llegan en grupos. Se ajusta una
    recta al tiempo de llegada contra el número de muestra: la pendiente es el periodo de muestreo.
    """
    n = np.arange(len(df))
    periodo, _ = np.polyfit(n, df["t_llegada"], 1)
    df.insert(0, "t", n * periodo)
    return 1 / periodo


def guardar_csv(df, carpeta, etiqueta):
    """Guarda la grabación como <etiqueta>_<número>.csv, con el siguiente número disponible."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    numero = 1
    while (carpeta / f"{etiqueta}_{numero:02d}.csv").exists():
        numero += 1
    ruta = carpeta / f"{etiqueta}_{numero:02d}.csv"
    df.to_csv(ruta, index=False, float_format="%.5f")
    return ruta


def cargar_grabaciones(carpeta):
    """Lee todos los CSV de la carpeta. Regresa una lista con un diccionario por grabación:
    archivo, etiqueta (el nombre sin el número), fs [Hz] y df (la tabla de datos)."""
    grabaciones = []
    for ruta in sorted(Path(carpeta).glob("*.csv")):
        df = pd.read_csv(ruta)
        grabaciones.append({
            "archivo": ruta.name,
            "etiqueta": ruta.stem.rsplit("_", 1)[0],
            "fs": (len(df) - 1) / df["t"].iloc[-1],
            "df": df,
        })
    return grabaciones


class SensorWT:
    """Conexión con un sensor WT9011DCL.

    Las notificaciones se reciben todo el tiempo mientras hay conexión, porque por ahí llegan
    tanto los datos como las respuestas a los comandos. Los datos solo se guardan durante grabar().
    """

    def __init__(self, direccion):
        self.cliente = BleakClient(direccion, timeout=20)
        self._buffer = bytearray()
        self._respuestas = {}
        self._muestras = []
        self._grabando = False

    async def conectar(self):
        await self.cliente.connect()
        await self.cliente.start_notify(UUID_DATOS, self._al_recibir)

    async def desconectar(self):
        if self.cliente.is_connected:
            await self.cliente.disconnect()

    def _al_recibir(self, _, datos):
        llegada = time.perf_counter()
        self._buffer.extend(datos)
        for p in separar_paquetes(self._buffer):
            if p[1] == 0x61 and self._grabando:
                self._muestras.append((llegada, p))
            elif p[1] == 0x71:
                registro = p[2] | (p[3] << 8)
                self._respuestas[registro] = struct.unpack("<8h", p[4:20])

    async def _enviar(self, *comando):
        await self.cliente.write_gatt_char(UUID_COMANDOS, bytes(comando), response=False)
        await asyncio.sleep(0.1)

    async def leer_registro(self, registro):
        """Pide al sensor el valor de un registro y espera la respuesta hasta 1 s."""
        self._respuestas.pop(registro, None)
        await self._enviar(0xFF, 0xAA, 0x27, registro, 0x00)
        for _ in range(20):
            if registro in self._respuestas:
                return self._respuestas[registro][0]
            await asyncio.sleep(0.05)
        raise TimeoutError(f"El sensor no respondió la lectura del registro 0x{registro:02X}")

    async def escribir_registro(self, registro, valor):
        """Desbloquea la configuración, escribe un registro de 16 bits y guarda el cambio en el sensor."""
        await self._enviar(0xFF, 0xAA, 0x69, 0x88, 0xB5)
        await self._enviar(0xFF, 0xAA, registro, valor & 0xFF, (valor >> 8) & 0xFF)
        await self._enviar(0xFF, 0xAA, 0x00, 0x00, 0x00)

    async def bateria(self):
        """Voltaje de la batería [V]."""
        return await self.leer_registro(REG_BATERIA) / 100

    async def temperatura(self):
        """Temperatura interna del sensor [°C]."""
        return await self.leer_registro(REG_TEMPERATURA) / 100

    async def frecuencia(self):
        """Frecuencia de muestreo configurada [Hz], o None si el código del registro no está en FRECUENCIAS."""
        codigo = await self.leer_registro(REG_FRECUENCIA)
        for hz, c in FRECUENCIAS.items():
            if c == codigo:
                return hz
        return None

    async def configurar_frecuencia(self, hz):
        if hz not in FRECUENCIAS:
            raise ValueError(f"Frecuencias disponibles: {list(FRECUENCIAS)} Hz")
        await self.escribir_registro(REG_FRECUENCIA, FRECUENCIAS[hz])

    async def grabar(self, duracion):
        """Graba durante `duracion` segundos. Regresa una tabla con una fila por muestra.

        La columna t_llegada es el momento en que el paquete llegó a la computadora,
        en segundos desde el primer paquete.
        """
        self._muestras = []
        self._grabando = True
        await asyncio.sleep(duracion)
        self._grabando = False

        llegadas = np.array([t for t, _ in self._muestras])
        df = pd.DataFrame([decodificar(p) for _, p in self._muestras])
        df.insert(0, "t_llegada", llegadas - llegadas[0])
        return df
