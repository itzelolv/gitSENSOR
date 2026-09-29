@echo off
rem Crea el entorno del curso: entorno virtual, librerías y kernel de Jupyter.
cd /d "%~dp0"

echo Creando el entorno virtual .venv ...
py -3.12 -m venv .venv 2>nul || python -m venv .venv
if not exist .venv\Scripts\python.exe (
    echo No se encontro Python. Instala Python 3.12 y vuelve a ejecutar este archivo.
    pause
    exit /b 1
)

echo Instalando librerias ...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo Registrando el kernel de Jupyter ...
.venv\Scripts\python.exe -m ipykernel install --user --name pds-wt9011 --display-name "Python (PDS WT9011)"

echo.
echo Listo. Abre esta carpeta en VS Code y empieza por 00_entorno.ipynb
pause
