### Структура проекта:

- Модульная архитектура с разделением на компоненты (хэндлеры, клавиатуры, БД, сервисы)
- Соответствует принципам чистого кода и легко расширяем

---

### Функциональность:

- Регистрация пользователей с выбором города
- Получение текущей погоды 
- Прогноз погоды на 5 дней 
- Еженедельный анализ погоды с тенденциями и прогнозом 
- Автоматическая отправка уведомлений о погоде каждое утро 
- Еженедельный аналитический отчет по воскресеньям

---

### Технические особенности:

- Использование aiogram 3.x для работы с Telegram API
- Асинхронная архитектура для высокой производительности
- SQLAlchemy для работы с базой данных
- Система логирования
- Планировщик задач для автоматизации отправки сообщений
- Конфигурация через .env файл для безопасности
- Docker для удобного развертывания
- Тесты для проверки работоспособности

---

### База данных:

- Таблица пользователей с информацией о городах
- Таблица погодных данных для аналитики

---

### Для запуска бота:

- Файл .env с токенами (Telegram и OpenWeatherMap)
- Запуск бота через Docker:
docker-compose up --build пересборка контейнера с заново
docker-compose up -d Запускает контейнеры в фоновом режиме (detached mode)
docker-compose logs -f bot  просмотреть логи контейнера
docker-compose down
docker-compose restart bot
docker exec -it skyvellum_bot /bin/bash  Если нужно войти в контейнер для отладки

docker-compose ps проверка работы контейнера
docker-compose logs bot проверка логов

- Или запустить локально: main.py