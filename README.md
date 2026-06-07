# Модуль сбора метрик для информационной системы самодиагностики

## Описание проекта

Модуль предназначен для централизованного сбора системных метрик с узлов информационной системы, их хранения в PostgreSQL, экспорта в Prometheus и визуализации в Grafana. Включает:
- **Агент** (Python) – сбор метрик CPU, памяти, диска, сети, процессов, uptime; пакетная отправка.
- **Ядро (Core)** (FastAPI) – приём метрик, валидация, сохранение в PostgreSQL, экспорт в Prometheus, авторизация JWT.
- **Консольный клиент (CLI)** – просмотр метрик, фильтрация, построение графиков.
- **Docker Compose** – контейнеризация PostgreSQL, Core, Prometheus, Grafana.

## Требования

- Операционная система: Windows 10/11 (Pro/Enterprise/Education) или Linux (Ubuntu 20.04+, Debian 11+)
- Установленный **Docker Desktop** (для Windows) или **Docker Engine** (для Linux)
- **Python 3.11+** (для запуска агента и CLI)
- **Git** (для клонирования)
- Свободные порты: 8000 (Core), 9090 (Prometheus), 3000 (Grafana), 5432 (PostgreSQL)

## Быстрый старт (автоматическое развёртывание)

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/Vasyuk1/metric-monitor.git
   cd metric-monitor
2. Запустите скрипт развёртывания (Windows):
deploy.bat
Скрипт установит зависимости Python, запустит контейнеры Docker и агента в отдельном окне.

3. После запуска станут доступны:
API Core: http://localhost:8000/docs
Prometheus: http://localhost:9090
Grafana: http://localhost:3000 (логин admin, пароль admin)

Ручное развёртывание (пошагово):

1. Запуск серверных компонентов (Docker):
Выполните в корневой папке проекта:
Командная строка:
bash
docker-compose up -d postgres core prometheus grafana

2. Запуск агента (локально):
Откройте новое окно терминала:
Командная строка:
bash
cd agent
pip install -r requirements.txt
python agent.py

3. Настройка Grafana (один раз):
Перейдите на http://localhost:3000, войдите (admin/admin).
Configuration → Data Sources → Add data source → Prometheus.
URL: http://prometheus:9090 → Save & Test.
Создайте дашборд с панелью, запрос cpu_usage.
