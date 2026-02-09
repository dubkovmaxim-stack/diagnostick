@echo off
chcp 65001 > nul
title СОЗДАНИЕ ФАЙЛОВ
echo ==================================================
echo        📄 СОЗДАНИЕ ФАЙЛОВ ДЛЯ БОТА
echo ==================================================
echo.
echo 📁 Папка: %CD%
echo.

REM Проверяем Python
set PYTHON_PATH=C:\Users\dubko\AppData\Local\Python\bin\python.exe
if not exist "%PYTHON_PATH%" (
    echo ❌ Локальный Python не найден
    echo    Сначала установите Python с python.org
    pause
    exit /b 1
)

echo ✅ Python: %PYTHON_PATH%
echo.

REM 1. Создаем requirements.txt
echo aiogram==3.5.0 > requirements.txt
echo python-dotenv==1.0.0 >> requirements.txt
echo aiofiles==23.2.1 >> requirements.txt
echo 📋 Создан requirements.txt

REM 2. Создаем .env (если нет)
if not exist ".env" (
    echo REPAIR_BOT_TOKEN=ваш_токен_здесь > .env
    echo REPAIR_ADMIN_ID=ваш_telegram_id >> .env
    echo 🔐 Создан .env (шаблон)
) else (
    echo ⚠️ .env уже существует
)

REM 3. Создаем bot.py (если нет)
if not exist "bot.py" (
    echo print("РЕМОНТ-БОТ") > bot.py
    echo print("Скопируйте сюда код из диалога") >> bot.py
    echo 🤖 Создан bot.py (шаблон)
) else (
    echo ⚠️ bot.py уже существует
)

echo.
echo ==================================================
echo ✅ ФАЙЛЫ СОЗДАНЫ!
echo.
echo 🚀 ИНСТРУКЦИЯ:
echo    1. Запустите install_repair.bat
echo    2. Откройте .env в Блокноте
echo       Вставьте токен бота
echo    3. Откройте bot.py в Блокноте
echo       Скопируйте полный код бота
echo    4. Запустите start_bot.bat
echo.
pause