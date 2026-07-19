@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

set CTRANSLATE2_CPU_ISA_TO_USE=GENERIC
set OMP_NUM_THREADS=1
set MKL_DEBUG_CPU_TYPE=5
set KMP_DUPLICATE_LIB_OK=TRUE

if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found, using system Python.
)

python main.py

if defined VIRTUAL_ENV (
    deactivate
)

pause