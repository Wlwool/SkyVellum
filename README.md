# SkyVellum - Ваш персональный метеоролог ☁️

SkyVellum - погодный бот, который следит за погодой за вас. Получайте актуальные данные, 
прогнозы и аналитические отчёты прямо в Telegram.

![Меню](https://github.com/Wlwool/SkyVellum/blob/main/images/menu.png)

## 🌟 Функциональность

✔️ Регистрация с выбором города  
✔️ Текущая погода  
✔️ Прогноз на 5 дней  
✔️ Еженедельный анализ погоды с тенденциями  
✔️ Авто-уведомления о погоде каждое утро  
✔️ Еженедельный аналитический отчёт по воскресеньям  

![Прогноз на 5 дней](https://github.com/Wlwool/SkyVellum/blob/main/images/5_day.png)

## ⚙️ Технические особенности

- **Язык**: Python 3.13  
- **Фреймворк**: aiogram 3.19.x  
- **Архитектура**: Асинхронная, модульная  
- **БД**: SQLAlchemy  
- **Логирование**: Встроенная система логов  
- **Планировщик задач**: Для отправки уведомлений  
- **Контейнеризация**: Docker  
- **Тестирование**: Автоматические тесты  

## 🛠️ Запуск бота

1. `.env` файл с токенами Telegram и OpenWeatherMap.
2. Запуск бота через Docker:
   ```sh
   docker-compose up --build  # Пересборка контейнера
   docker-compose up -d  # Запуск в фоновом режиме
   ```
3. Управление контейнером:
   ```sh
   docker-compose logs -f bot  # Просмотр логов
   docker-compose down  # Остановка контейнера
   docker-compose restart bot  # Перезапуск
   docker exec -it skyvellum_bot /bin/bash  # Вход в контейнер
   ```

## 🗄️ База данных

- **users** — хранит информацию о пользователях и их городах  
- **weather_data** — исторические данные для аналитики  

## 📸 Примеры работы

### Утренний прогноз
![Утренний прогноз](https://github.com/Wlwool/SkyVellum/blob/main/images/8_00_utro.png)

### Еженедельный отчёт
![Еженедельный отчёт](https://github.com/Wlwool/SkyVellum/blob/main/images/12_00_sun.png)

### Текущая погода
![Погода сейчас](https://github.com/Wlwool/SkyVellum/blob/main/images/weather_now.png)

## 📩 Обратная связь
Есть идеи или вопросы? Открывайте issue или создавайте pull request в [репозитории](https://github.com/Wlwool/SkyVellum).
