# Используем официальный легковесный образ Python 3.14
FROM python:3.14-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости (если их нет, строку можно удалить/закомментировать)
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все исходники проекта в контейнер
COPY . .

# Запускаем скрипт как модуль (флаг -u отключает буферизацию логов, чтобы print() сразу шли в консоль)
CMD ["python", "-u", "-m", "server.main"]
