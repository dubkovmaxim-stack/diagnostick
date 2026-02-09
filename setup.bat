@echo off
echo Создание ремонт-бота в C:\Users\dubko\OneDrive\Desktop\botrepair
echo.

echo Создаю файлы...
echo. > bot.py
echo. > .env
echo. > requirements.txt
echo. > run.bat

echo Заполняю requirements.txt...
echo aiogram==3.5.0 > requirements.txt
echo python-dotenv==1.0.0 >> requirements.txt
echo aiofiles==23.2.1 >> requirements.txt

echo Заполняю .env шаблоном...
echo REPAIR_BOT_TOKEN=ваш_токен_здесь > .env
echo REPAIR_ADMIN_ID=ваш_telegram_id >> .env

echo Создаю run.bat...
echo @echo off > run.bat
echo echo Запуск ремонт-бота... >> run.bat
echo python bot.py >> run.bat
echo pause >> run.bat

echo.
echo ✅ Готово!
echo.
echo 1. Открой файл .env и замени ваш_токен_здесь на реальный токен бота
echo 2. Запусти install.bat для установки зависимостей
echo 3. Запусти run.bat для запуска бота
echo.
pause