from prometheus_client import Gauge, REGISTRY

class MetricsRegistry:
    def __init__(self):
        self._gauges = {}

    def set_gauge(self, name: str, value: float, labels: dict = None):
        # Если метрика ещё не создана — создаём
        if name not in self._gauges:
            if labels:
                self._gauges[name] = Gauge(name, 'auto-generated', list(labels.keys()))
            else:
                self._gauges[name] = Gauge(name, 'auto-generated')
        # Устанавливаем значение
        if labels:
            self._gauges[name].labels(**labels).set(value)
        else:
            self._gauges[name].set(value)

registry = MetricsRegistry()