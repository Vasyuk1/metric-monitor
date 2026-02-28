from prometheus_client import Gauge, REGISTRY
import re

def sanitize_label_name(name: str) -> str:
    """Заменяет недопустимые символы в имени метки на подчёркивание."""
    # Первый символ должен быть буквой или подчёркиванием
    if not re.match(r'^[a-zA-Z_]', name):
        name = '_' + name
    # Остальные символы: буквы, цифры, подчёркивание
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    return name

class MetricsRegistry:
    def __init__(self):
        self._gauges = {}

    def set_gauge(self, name: str, value: float, labels: dict = None):
        if name not in self._gauges:
            if labels:
                # Очищаем имена меток
                safe_labels = [sanitize_label_name(k) for k in labels.keys()]
                self._gauges[name] = Gauge(name, 'auto-generated', safe_labels)
            else:
                self._gauges[name] = Gauge(name, 'auto-generated')
        if labels:
            # Создаём словарь с очищенными именами и исходными значениями
            safe_labels_dict = {sanitize_label_name(k): v for k, v in labels.items()}
            self._gauges[name].labels(**safe_labels_dict).set(value)
        else:
            self._gauges[name].set(value)

registry = MetricsRegistry()