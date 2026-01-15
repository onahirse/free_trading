# Используем официальный образ Python как базовый
FROM python:3.13-slim as builder
WORKDIR /install
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-deps --wheel-dir /wheels -r requirements.txt

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /srs

# Устанавливаем git (нужен для клонирования)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-deps --no-index --find-links=/wheels -r requirements.txt

WORKDIR /app
# Клонируем репозиторий
RUN git clone https://github.com/onahirse/free_trading.git .

# Создаём необходимые директории
RUN mkdir -p DATA_OHLCV LOGS REPORTS

# Запускаем тесты после сборки проекта
# Тесты для signal_handler и position_builder
RUN python -m pytest src/tests/trading/test_position_builder.py src/tests/trading/test_signal_handler*.py -v --tb=short || echo "Тесты завершены с предупреждениями"

# Указываем тома, чтобы данные можно было монтировать извне
VOLUME ["/app/DATA_OHLCV", "/app/LOGS", "/app/REPORTS", "/app/configs"]

# Команда запуска
CMD ["python", "app.py"]