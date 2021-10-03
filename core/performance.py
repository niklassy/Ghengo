import time


class _PerformanceMeasurement:
    def __init__(self):
        self._start_time_map = {}
        self._result_time_map = {}

    def reset(self):
        self._start_time_map = {}
        self._result_time_map = {}

    def start_measure(self, key):
        self._start_time_map[key] = time.time()

    def end_measure(self, key):
        if key not in self._start_time_map:
            raise ValueError()

        self._result_time_map[key] = time.time() - self._start_time_map[key]
        del self._start_time_map[key]

    def times_measured(self, key):
        return 1 if key in self._result_time_map else 0

    def get_time_for(self, key):
        if key not in self._result_time_map:
            raise ValueError()

        return self._result_time_map[key]

    def get_print_keys(self):
        return [key for key in self._result_time_map]

    def get_print_message(self, key):
        return '{} took {} ({} times measured)'.format(
                key, round(self.get_time_for(key), 2), self.times_measured(key))

    def print_all(self):
        for key in self.get_print_keys():
            print(self.get_print_message(key))


class _MultiplePerformanceMeasurementBase(_PerformanceMeasurement):
    def end_measure(self, key):
        if key not in self._start_time_map:
            return

        self.add_value_to_measured(key, time.time() - self._start_time_map[key])
        del self._start_time_map[key]

    def add_value_to_measured(self, key, value):
        if key in self._result_time_map:
            current_value = self._result_time_map[key]
        else:
            current_value = []

        current_value.append(value)
        self._result_time_map[key] = current_value

    def get_print_keys(self):
        return sorted(super().get_print_keys())

    def times_measured(self, key):
        return len(self._result_time_map.get(key, []))


class _SumPerformanceMeasurement(_MultiplePerformanceMeasurementBase):
    def get_time_for(self, key):
        return sum(super().get_time_for(key))


class _AveragePerformanceMeasurement(_MultiplePerformanceMeasurementBase):
    def get_time_for(self, key):
        all_times = super().get_time_for(key)
        return sum(all_times) / len(all_times)


PerformanceMeasurement = _PerformanceMeasurement()
SumPerformanceMeasurement = _SumPerformanceMeasurement()
AveragePerformanceMeasurement = _AveragePerformanceMeasurement()
