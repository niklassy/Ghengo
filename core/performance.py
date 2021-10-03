import time

from gherkin.ast import Given, When, Then


class MeasureKeys:
    NLP = '---- NLP'
    STEP = '----- STEP_'


class _PerformanceMeasurement:
    def __init__(self):
        self._start_time_map = {}
        self.result_time_map = {}

    def reset(self):
        self._start_time_map = {}
        self.result_time_map = {}

    def start_measure(self, key):
        key = self.get_key(key)
        self._start_time_map[key] = time.time()

    def get_key(self, key):
        return key

    def end_measure(self, key):
        key = self.get_key(key)

        if key not in self._start_time_map:
            raise ValueError()

        self.result_time_map[key] = time.time() - self._start_time_map[key]
        del self._start_time_map[key]

    def times_measured(self, key):
        return 1 if key in self.result_time_map else 0

    def get_time_for(self, key):
        if key not in self.result_time_map:
            raise ValueError()

        return self.result_time_map[key]

    def get_print_keys(self):
        return [key for key in self.result_time_map]

    def get_print_message(self, key):
        return '{} took {} ({} times measured)'.format(
                key, round(self.get_time_for(key), 2), self.times_measured(key))

    def print_all(self):
        for key in self.get_print_keys():
            print(self.get_print_message(key))

    def add_value_to_measured(self, key, value):
        if key in self.result_time_map:
            current_value = self.result_time_map[key]
        else:
            current_value = []

        current_value.append(value)
        self.result_time_map[key] = current_value

    def export_to_other(self, other: '_PerformanceMeasurement'):
        for key in self.result_time_map:
            other.add_value_to_measured(key, self.get_time_for(key))


class _MultiplePerformanceMeasurementBase(_PerformanceMeasurement):
    def end_measure(self, key):
        key = self.get_key(key)

        if key not in self._start_time_map:
            return

        self.add_value_to_measured(key, time.time() - self._start_time_map[key])
        del self._start_time_map[key]

    def get_print_keys(self):
        return sorted(super().get_print_keys())

    def times_measured(self, key):
        return len(self.result_time_map.get(key, []))


class _SumPerformanceMeasurement(_MultiplePerformanceMeasurementBase):
    def get_time_for(self, key):
        return sum(super().get_time_for(key))


class _AveragePerformanceMeasurement(_MultiplePerformanceMeasurementBase):
    def get_time_for(self, key):
        all_times = super().get_time_for(key)
        return sum(all_times) / len(all_times)


class _StepLevelPerformanceMeasurement(_SumPerformanceMeasurement):
    STEP_GIVEN = '01_GIVEN'
    STEP_WHEN = '02_WHEN'
    STEP_THEN = '03_THEN'

    def __init__(self):
        super().__init__()
        self.step_type = None

    def get_key(self, key):
        return '{}__{}'.format(key, self.step_type)

    def set_step_type(self, step):
        step_to_type = {
            Given: self.STEP_GIVEN,
            When: self.STEP_WHEN,
            Then: self.STEP_THEN,
        }

        self.step_type = step_to_type[step]


PerformanceMeasurement = _PerformanceMeasurement()
SumPerformanceMeasurement = _SumPerformanceMeasurement()
ScenarioLevelPerformanceMeasurement = _SumPerformanceMeasurement()
StepLevelPerformanceMeasurement = _StepLevelPerformanceMeasurement()
AveragePerformanceMeasurement = _AveragePerformanceMeasurement()
