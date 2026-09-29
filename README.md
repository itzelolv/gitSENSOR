# Procesamiento digital de señales con el sensor WT9011DCL

Material de la clase de procesamiento digital de señales previa a Machine Learning. Se trabaja con el sensor inercial WT9011DCL de WitMotion (acelerómetro, giroscopio y ángulos), que se conecta por Bluetooth Low Energy. A lo largo de los notebooks se adquieren señales de movimiento, se procesan y se preparan como conjunto de datos para entrenar un modelo.

## Requisitos

- Windows 10 u 11 con Bluetooth
- [Python 3.12](https://www.python.org/downloads/)
- [Visual Studio Code](https://code.visualstudio.com/) con las extensiones Python y Jupyter
- [Git](https://git-scm.com/downloads)
- Un sensor WT9011DCL con batería cargada

## Instalación

Clonar el repositorio:

```
git clone https://github.com/jechairez/pds-wt9011.git
```

Entrar a la carpeta y hacer doble clic en `instalar.bat`. El archivo crea el entorno virtual `.venv`, instala las librerías de `requirements.txt` y registra el kernel "Python (PDS WT9011)" en Jupyter. Tarda unos minutos.

Si se prefiere hacerlo a mano, desde una terminal en la carpeta del repositorio:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m ipykernel install --user --name pds-wt9011 --display-name "Python (PDS WT9011)"
```

Después, en VS Code: File, Open Folder, y seleccionar la carpeta del repositorio. Al abrir un notebook, elegir el kernel "Python (PDS WT9011)" o el intérprete `.venv`.

## Notebooks

| Notebook | Contenido |
|---|---|
| `00_entorno` | verificación de Python, librerías, gráficas y Bluetooth |
| `01_conexion` | conexión con el sensor, estructura de los paquetes y decodificación |
| `02_adquisicion` | frecuencia de muestreo configurada y real, grabación de actividades en CSV |
| `03_visualizacion` | lectura de las señales, magnitudes, comparación entre actividades, revisión de calidad |
| `04_preprocesamiento` | recorte, filtro pasa-bajas Butterworth, separación de la gravedad |
| `05_normalizacion` | z-score, min-max y escalado robusto; fuga de datos |
| `06_frecuencia` | FFT, densidad espectral de potencia (Welch) y espectrograma |

Los notebooks 00 a 02 necesitan el sensor. Del 03 en adelante trabajan con archivos CSV y se pueden seguir con los datos de ejemplo de `datos/demo`.

## Estructura

```
wt9011.py           comunicación con el sensor: conexión, decodificación, grabación
procesamiento.py    filtros, separación de la gravedad y magnitudes
requirements.txt    librerías con versiones fijas
instalar.bat        instalación del entorno en Windows
datos/demo/         grabaciones de ejemplo: caminar, quieto y recta, 5 de cada una
```

Cada equipo guarda sus grabaciones en `datos/equipo_A` o `datos/equipo_B` y cambia la variable `CARPETA` al inicio de cada notebook.

## Notas

- Las versiones de las librerías están fijas en `requirements.txt`. Las más recientes de numpy, scipy y pandas son bloqueadas por Smart App Control en algunas computadoras con Windows 11, y la serie 7 de ipykernel se queda colgada al conectar en algunas versiones de VS Code.
- Un sensor BLE acepta una sola conexión a la vez. Si no aparece en el escaneo, revisar que no esté conectado a otra computadora o a la aplicación del celular.
- Al terminar de usar el sensor hay que ejecutar la celda de desconexión; si no, el sensor sigue ocupado.
