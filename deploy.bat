@echo off
chcp 65001 > nul
echo ========================================
echo   Развёртывание системы сбора метрик
echo ========================================
echo.

REM Проверка наличия Python (через python или py)
set PYTHON_CMD=python
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python не найден. Установите Python 3.8+ и добавьте в PATH.
        exit /b 1
    ) else (
        set PYTHON_CMD=py
        echo [OK] Python найден (через py)
    )
) else (
    echo [OK] Python найден (через python)
)

REM Проверка наличия Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker не найден. Установите Docker Desktop.
    exit /b 1
)
echo [OK] Docker найден.

REM Установка зависимостей для core
echo Установка зависимостей core...
cd core
%PYTHON_CMD% -m pip install -r requirements.txt > nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ошибка при установке зависимостей core, возможно, они уже есть.
)
cd ..

REM Установка зависимостей для agent
echo Установка зависимостей agent...
cd agent
%PYTHON_CMD% -m pip install -r requirements.txt > nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ошибка при установке зависимостей agent, возможно, они уже есть.
)
cd ..

REM Установка зависимостей для клиента (metrics_cli.py)
echo Установка зависимостей для клиента...
%PYTHON_CMD% -m pip install requests tabulate matplotlib > nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ошибка при установке зависимостей клиента, возможно, они уже есть.
)

REM Запуск Docker-стека (PostgreSQL, core, Prometheus, Grafana)
echo Запуск PostgreSQL, core, Prometheus, Grafana...
docker-compose up -d postgres core prometheus grafana
if errorlevel 1 (
    echo [ERROR] Не удалось запустить Docker-стек. Проверьте Docker.
    exit /b 1
)
echo [OK] Docker-стек запущен.

REM Небольшая пауза, чтобы core успел инициализировать БД
timeout /t 5 /nobreak > nul

REM Запуск агента в отдельном окне
echo Запуск агента...
start "Agent" cmd /c "cd agent && %PYTHON_CMD% agent.py"

REM Запуск интерактивного клиента в текущем окне
echo.
echo ========================================
echo   Запуск интерактивного клиента...
echo ========================================
%PYTHON_CMD% metrics_cli.py

echo.
echo Работа клиента завершена. Для выхода нажмите любую клавишу...
pause > nul