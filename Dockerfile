FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Обновляем пакеты и устанавливаем зависимости
RUN apt-get update && apt-get install -y gcc libpq-dev postgresql-client && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем всё содержимое текущей директории в /app контейнера
COPY . .

# Делаем entrypoint исполняемым
RUN chmod +x ./entrypoint.sh

# Открываем порт
EXPOSE 8000

# Запускаем приложение
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
