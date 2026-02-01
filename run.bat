@echo off
chcp 65001 >nul
echo ═══════════════════════════════════════════════════════
echo              MitaHelper - Запуск бота
echo ═══════════════════════════════════════════════════════
echo.

REM Проверяем наличие виртуального окружения
if not exist "venv" (
    echo [*] Создание виртуального окружения...
    python -m venv venv
)

REM Активируем виртуальное окружение
call venv\Scripts\activate.bat

REM Проверяем зависимости
echo [*] Проверка зависимостей...
pip install -q -r requirements.txt

echo.
echo [*] Запуск бота...
echo ═══════════════════════════════════════════════════════
echo.

python -m MitaHelper

pause
