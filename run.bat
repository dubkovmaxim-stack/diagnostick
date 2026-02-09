@echo off
echo ========================================
echo  РЕМОНТ АУДИТ БОТ - УЛУЧШЕННАЯ ВЕРСИЯ
echo ========================================
echo.

cd /d "C:\Users\dubko\OneDrive\Desktop\botrepair"
python bot2.py
pause


REM Активация виртуального окружения
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ❌ Виртуальное окружение не найдено
    echo Создайте его: python -m venv venv
    pause
    exit /b 1
)

REM Установка зависимостей если нужно
echo 📦 Проверяю зависимости...
pip install -r requirements.txt > nul 2>&1

REM Запуск бота
echo 🚀 Запускаю улучшенную версию бота...
echo.
python bot2.py

pause