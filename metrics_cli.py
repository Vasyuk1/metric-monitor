#!/usr/bin/env python3
import sys
import os
import json
import argparse
import subprocess
import requests
from tabulate import tabulate
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
TOKEN_FILE = ".token"
SESSION_FILE = ".session"

def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        f.write(token)

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    return None

def save_session(role, login):
    with open(SESSION_FILE, "w") as f:
        f.write(f"{role}\n{login}")

def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            role = f.readline().strip()
            login = f.readline().strip()
            return role, login
    return None, None

def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

def get_headers():
    token = load_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def api_request(method, endpoint, data=None, params=None):
    url = f"{BASE_URL}{endpoint}"
    headers = get_headers()
    if data is not None:
        headers["Content-Type"] = "application/json"
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError("Unsupported method")
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Ответ сервера: {e.response.text}")
        return None

def cmd_register(login, password):
    data = {"login": login, "password": password}
    result = api_request("POST", "/api/auth/register", data=data)
    if result:
        print(result.get("msg", "Регистрация успешна"))

def cmd_login(login, password):
    data = {"login": login, "password": password}
    result = api_request("POST", "/api/auth/login", data=data)
    if result:
        token = result.get("access_token")
        role = result.get("role")
        login = result.get("login")
        if token:
            save_token(token)
            save_session(role, login)
            print(f"Успешный вход. Роль: {role}")
        else:
            print("Ошибка: токен не получен")

def cmd_list(limit=100, offset=0, sort="desc", agent=None, metric=None, from_time=None, to_time=None):
    params = {
        "limit": limit,
        "offset": offset,
        "sort": sort,
    }
    if agent:
        params["agent"] = agent
    if metric:
        params["metric_name"] = metric
    if from_time:
        params["from_time"] = from_time
    if to_time:
        params["to_time"] = to_time
    result = api_request("GET", "/api/v1/metrics/query", params=params)
    if not result:
        return
    total = result.get("total", 0)
    metrics = result.get("metrics", [])
    print(f"Всего записей: {total}, показано {len(metrics)} (limit={result['limit']}, offset={result['offset']})")
    if not metrics:
        print("Нет данных.")
        return
    table = []
    for m in metrics:
        dt = datetime.fromtimestamp(m["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        table.append([m["agent_id"], m["name"], m["value"], dt, json.dumps(m["tags"])])
    headers = ["Agent", "Metric", "Value", "Time", "Tags"]
    print(tabulate(table, headers=headers, tablefmt="grid"))

def cmd_plot(metric_name, hours=1):
    to_time = int(datetime.now().timestamp())
    from_time = int((datetime.now() - timedelta(hours=hours)).timestamp())
    params = {
        "metric_name": metric_name,
        "from_time": from_time,
        "to_time": to_time,
        "sort": "asc",
        "limit": 10000
    }
    result = api_request("GET", "/api/v1/metrics/query", params=params)
    if not result:
        return
    metrics = result.get("metrics", [])
    if not metrics:
        print(f"Нет данных для метрики '{metric_name}' за последние {hours} часов.")
        return
    points = {}
    for m in metrics:
        ts = m["timestamp"]
        val = m["value"]
        points.setdefault(ts, []).append(val)
    timestamps = sorted(points.keys())
    values = [sum(points[ts]) / len(points[ts]) for ts in timestamps]
    dates = [datetime.fromtimestamp(ts) for ts in timestamps]
    plt.figure(figsize=(10, 6))
    plt.plot(dates, values, marker='o', linestyle='-')
    plt.title(f"Метрика: {metric_name} (последние {hours} ч)")
    plt.xlabel("Время")
    plt.ylabel("Значение")
    plt.grid(True)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.gcf().autofmt_xdate()
    filename = f"plot_{metric_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=150)
    print(f"График сохранён в {filename}")

def cmd_run_tests():
    print("Запуск тестов API...")
    result = subprocess.run(["python", "-m", "pytest", "tests/test_api.py", "-v"], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("Ошибки тестов:")
        print(result.stderr)

def cmd_stop_agent():
    """Останавливает агента (закрывает окно) и останавливает Docker-контейнеры."""
    print("Останавливаем агента...")
    # Завершаем процесс python.exe, который запущен с заголовком "Agent"
    # (это работает, если в deploy.bat запуск агента был с заголовком)
    os.system("taskkill /F /FI \"WINDOWTITLE eq Agent*\" /IM python.exe > nul 2>&1")
    print("Останавливаем Docker-контейнеры...")
    os.system("docker-compose down")
    print("Все компоненты остановлены. Нажмите Enter для выхода.")
    input()

def interactive_mode():
    role, login = load_session()
    while True:
        print("\n" + "="*50)
        print("   МЕТРИКИ COLLECTOR CLI")
        if login:
            print(f"   Пользователь: {login} (роль: {role})")
        print("="*50)
        print("1. Регистрация")
        print("2. Вход (авторизация)")
        print("3. Просмотр метрик")
        print("4. Построить график метрики")
        if role == "admin":
            print("5. Запустить тесты API (только админ)")
        print("6. Остановить агента и сервер")
        print("0. Выход")
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            login = input("Логин: ")
            password = input("Пароль: ")
            cmd_register(login, password)
        elif choice == "2":
            login = input("Логин: ")
            password = input("Пароль: ")
            cmd_login(login, password)
            role, login = load_session()
        elif choice == "3":
            if not load_token():
                print("Вы не авторизованы. Сначала выполните вход (пункт 2).")
                continue
            print("\n--- Фильтры (оставьте пустым, если не нужно) ---")
            agent = input("Agent ID: ").strip() or None
            metric = input("Имя метрики (cpu_usage, memory_usage и др.): ").strip() or None
            limit = input("Количество записей (по умолчанию 100): ").strip()
            limit = int(limit) if limit else 100
            sort = input("Сортировка по времени (desc/asc, по умолчанию desc): ").strip()
            if sort not in ["asc", "desc"]:
                sort = "desc"
            from_time = input("Начало периода (Unix timestamp, опционально): ").strip()
            from_time = int(from_time) if from_time else None
            to_time = input("Конец периода (Unix timestamp, опционально): ").strip()
            to_time = int(to_time) if to_time else None
            cmd_list(limit=limit, sort=sort, agent=agent, metric=metric,
                     from_time=from_time, to_time=to_time)
        elif choice == "4":
            if not load_token():
                print("Вы не авторизованы. Сначала выполните вход (пункт 2).")
                continue
            metric = input("Имя метрики (например, cpu_usage): ").strip()
            if not metric:
                print("Имя метрики обязательно.")
                continue
            hours = input("Период в часах (по умолчанию 1): ").strip()
            hours = int(hours) if hours else 1
            cmd_plot(metric, hours)
        elif choice == "5" and role == "admin":
            cmd_run_tests()
        elif choice == "6":
            cmd_stop_agent()
            break
        elif choice == "0":
            print("До свидания!")
            break
        else:
            print("Неверный выбор. Попробуйте снова.")

def main():
    if len(sys.argv) == 1:
        interactive_mode()
        return

    # Для продвинутых пользователей: аргументы командной строки
    parser = argparse.ArgumentParser(description="Metrics Collector CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_register = subparsers.add_parser("register", help="Регистрация")
    p_register.add_argument("login")
    p_register.add_argument("password")
    p_register.set_defaults(func=lambda args: cmd_register(args.login, args.password))

    p_login = subparsers.add_parser("login", help="Вход")
    p_login.add_argument("login")
    p_login.add_argument("password")
    p_login.set_defaults(func=lambda args: cmd_login(args.login, args.password))

    p_list = subparsers.add_parser("list", help="Показать метрики")
    p_list.add_argument("--agent", help="Фильтр по agent_id")
    p_list.add_argument("--metric", help="Фильтр по имени метрики")
    p_list.add_argument("--limit", type=int, default=100)
    p_list.add_argument("--offset", type=int, default=0)
    p_list.add_argument("--sort", choices=["asc", "desc"], default="desc")
    p_list.add_argument("--from-time", type=int)
    p_list.add_argument("--to-time", type=int)
    p_list.set_defaults(func=lambda args: cmd_list(args.limit, args.offset, args.sort,
                                                   args.agent, args.metric,
                                                   args.from_time, args.to_time))

    p_plot = subparsers.add_parser("plot", help="Построить график")
    p_plot.add_argument("metric", help="Имя метрики")
    p_plot.add_argument("--hours", type=int, default=1)
    p_plot.set_defaults(func=lambda args: cmd_plot(args.metric, args.hours))

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()