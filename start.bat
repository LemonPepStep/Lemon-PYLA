@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Lemon-PYLA
color 0A

cd /d "%~dp0"

set "VENV_DIR=venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "DEPS_OK=%VENV_DIR%\.deps_ok"
set "FORCE_DEPS=0"

if /i "%~1"=="--reinstall"  set "FORCE_DEPS=1"
if /i "%~1"=="--force-deps" set "FORCE_DEPS=1"

echo.
echo ===============================================
echo         PylaAI-OP - Brawl Stars Automation
echo ===============================================
echo.

REM ---------- Step 1: venv ----------
if not exist "%VENV_PY%" (
    call :find_python
    if errorlevel 1 goto :python_missing
    echo [INFO] Creating virtual environment with %PYTHON_CMD% ...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 goto :venv_failed
    set "FORCE_DEPS=1"
)

if not exist "%VENV_PY%" goto :venv_failed

REM ---------- Step 2: dep check ----------
set "NEED_INSTALL=0"

if "!FORCE_DEPS!"=="1" (
    echo [INFO] Reinstall requested.
    set "NEED_INSTALL=1"
    goto :maybe_install
)

if not exist "%DEPS_OK%" (
    echo [INFO] First launch or dependency marker missing.
    set "NEED_INSTALL=1"
    goto :maybe_install
)

"%VENV_PY%" -c "import PySide6, numpy, cv2, onnxruntime" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Core packages missing - reinstalling.
    set "NEED_INSTALL=1"
    goto :maybe_install
)

echo [OK] Dependencies verified - skipping install.

:maybe_install
if "!NEED_INSTALL!"=="1" (
    echo.
    echo [INFO] Installing / updating dependencies...
    "%VENV_PY%" -m pip install --upgrade pip setuptools wheel >nul
    if exist "setup.py" (
        "%VENV_PY%" -m pip install -e .
        if errorlevel 1 goto :install_failed
    )
    "%VENV_PY%" -c "import PySide6" >nul 2>&1
    if errorlevel 1 (
        "%VENV_PY%" -m pip install PySide6
        if errorlevel 1 goto :install_failed
    )
    >"%DEPS_OK%" echo ok
    echo [OK] Dependencies ready.
)

REM ---------- Step 3: CUDA / GPU setup ----------
set "ORT_LOGGING_LEVEL=3"

set "CUDA_BIN=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin"
if exist "%CUDA_BIN%\cublas64_12.dll" (
    set "PATH=%CUDA_BIN%;%PATH%"
    echo [GPU] CUDA 12.6 bin added to PATH.
)

REM TensorRT DLLs — check bundled path first, then Downloads fallback
set "TRT_LIB="
if exist "%~dp0tensorrt\lib\nvinfer_10.dll" set "TRT_LIB=%~dp0tensorrt\lib"
if not defined TRT_LIB if exist "%USERPROFILE%\Downloads\TensorRT-10.10.0.31\lib\nvinfer_10.dll" set "TRT_LIB=%USERPROFILE%\Downloads\TensorRT-10.10.0.31\lib"
if defined TRT_LIB (
    set "PATH=!TRT_LIB!;%PATH%"
    set "TRT_LIB_PATH=!TRT_LIB!"
    echo [GPU] TensorRT 10 lib found and added to PATH.
) else (
    echo [GPU] TensorRT not found - running with CUDA only.
)

nvidia-smi >nul 2>&1
if not errorlevel 1 (
    "%VENV_PY%" -c "import onnxruntime as o; assert 'CUDAExecutionProvider' in o.get_available_providers()" >nul 2>&1
    if errorlevel 1 (
        echo [GPU] Installing onnxruntime-gpu...
        "%VENV_PY%" -m pip install onnxruntime-gpu >nul
    )
    "%VENV_PY%" -c "import torch; assert torch.cuda.is_available()" >nul 2>&1
    if errorlevel 1 (
        echo [GPU] Installing PyTorch CUDA 12.6 build - this may take a few minutes...
        "%VENV_PY%" -m pip install --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu126 --no-deps >nul
        echo [GPU] PyTorch CUDA build installed.
    )
    echo [GPU] CUDA GPU ready - RTX detected.
)

REM ---------- Step 4: launch ----------
echo.
echo [INFO] Starting PylaAI-OP...
echo ===============================================
echo.

"%VENV_PY%" main.py
set "RC=!ERRORLEVEL!"

echo.
if "!RC!"=="0" (
    echo [INFO] PylaAI-OP exited cleanly.
) else (
    color 0C
    echo ERROR: Application exited with code !RC!
)
echo.
pause
exit /b !RC!


REM ==================== helpers ====================
:find_python
where py.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    py -3.13 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 ( set "PYTHON_CMD=py -3.13" & exit /b 0 )
    py -3.12 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 ( set "PYTHON_CMD=py -3.12" & exit /b 0 )
    py -3.11 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 ( set "PYTHON_CMD=py -3.11" & exit /b 0 )
    py -3 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 ( set "PYTHON_CMD=py -3" & exit /b 0 )
)
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 ( set "PYTHON_CMD=python" & exit /b 0 )
exit /b 1

:python_missing
color 0C
echo ERROR: Python is not installed or not on PATH.
echo Install Python 3.13 from https://www.python.org/ and relaunch.
echo.
pause
exit /b 1

:venv_failed
color 0C
echo ERROR: Could not create or locate the virtual environment at "%VENV_DIR%".
echo Delete the "venv" folder and try again.
echo.
pause
exit /b 1

:install_failed
color 0C
echo.
echo ERROR: Dependency install failed. Re-run with --reinstall after fixing the issue.
echo.
pause
exit /b 1
