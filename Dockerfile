# ═══════════════════════════════════════════════════════════════
#                    MitaHelper - Dockerfile
# ═══════════════════════════════════════════════════════════════

FROM python:3.11-slim

# Метаданные
LABEL maintainer="MitaHelper"
LABEL description="Telegram Bot for Group Management"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем requirements первым для кэширования слоя
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY . .

# Создаем директорию для данных
RUN mkdir -p /app/MitaHelper/data

# Том для персистентных данных
VOLUME ["/app/MitaHelper/data"]

# Запуск бота
CMD ["python", "-m", "MitaHelper"]
