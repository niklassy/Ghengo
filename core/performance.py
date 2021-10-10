import time

from gherkin.ast import Given, When, Then, Step
from settings import Settings


class MeasureKeys:
    NLP = '---- NLP'
    STEP = '----- STEP_'
    SCENARIO = '--- GENERATOR_SCENARIO'
    LOOKOUT_STEP = '----------- LOCATE_ST'
    LOOKOUT_SCENARIO = '----------- LOCATE_SC'
    TILER_BEST_CONVERTER = '------- FIND_BEST_CONVERTER'
    TILER_STATEMENTS = '------- GET_STATEMENTS_'
    LEXER_PARSER = '--- LEXER + PARSER'
    EXTRACTOR = '----------- Extractor'
    CONVERTER_REFERENCES = '--------- CONVERTER__FIND_REFERENCES_'
    EVERYTHING = '------------------ EVERYTHING'
    MODEL_INIT = '- 0 MODEL INIT'
    GENERATION = '- 1 GENERATION'


class _PerformanceMeasurement:
    """
    A class that can be used to analyze the performance of Ghengo.
    """
    def __init__(self):
        self._start_time_map = {}
        self._result_time_map = {}

    def reset(self):
        """Reset the instance."""
        self._start_time_map = {}
        self._result_time_map = {}

    def start_measure(self, key):
        """Start to measure at a given point. You must call `end_measure`. To stop the measurement."""
        key = self.get_key(key)
        self._start_time_map[key] = time.time()

    def get_key(self, string):
        """Returns the key that will be used to save the values in the result_time_map."""
        return string

    def end_measure(self, key):
        """Ends the measurement for a given key. If the key does not exist, this method will simply ignore it."""
        key = self.get_key(key)

        if key not in self._start_time_map:
            return

        self._result_time_map[key] = time.time() - self._start_time_map[key]
        del self._start_time_map[key]

    def times_measured(self, key):
        """Returns the number of times a key was measured."""
        return 1 if key in self._result_time_map else 0

    def get_time_for(self, key):
        """Returns the time value from a previous measurement for a given key."""
        if key not in self._result_time_map:
            raise ValueError()

        return self._result_time_map[key]

    def _get_print_keys(self):
        """Returns all keys that will be printed. This is used by `print_measurements`."""
        return [key for key in self._result_time_map]

    def _get_print_message(self, key):
        """Returns the message for each key that is printed in `print_measurements`."""
        return '{} took {} ({} times measured)'.format(
                key, round(self.get_time_for(key), 2), self.times_measured(key))

    def print_measurements(self):
        """Prints all the the information about all measurements of this instance."""
        for key in self._get_print_keys():
            print(self._get_print_message(key))

    def add_value_to_measured(self, key, value):
        """Can be used to manually add a measurement to the _result_time_map."""
        if key in self._result_time_map:
            current_value = self._result_time_map[key]
        else:
            current_value = []

        current_value.append(value)
        self._result_time_map[key] = current_value

    def export_to_other(self, other: '_PerformanceMeasurement'):
        """Export all values to another _PerformanceMeasurement instance."""
        for key in self._result_time_map:
            other.add_value_to_measured(key, self.get_time_for(key))


class _MultiplePerformanceMeasurementBase(_PerformanceMeasurement):
    """This class is a base class that can be used to store multiple values for a single key."""
    def end_measure(self, key):
        key = self.get_key(key)

        if key not in self._start_time_map:
            return

        self.add_value_to_measured(key, time.time() - self._start_time_map[key])
        del self._start_time_map[key]

    def _get_print_keys(self):
        return sorted(super()._get_print_keys())

    def times_measured(self, key):
        return len(self._result_time_map.get(key, []))


class _SumPerformanceMeasurement(_MultiplePerformanceMeasurementBase):
    """This will take the sum of all measured times for a key."""
    def get_time_for(self, key):
        return sum(super().get_time_for(key))


class _AveragePerformanceMeasurement(_MultiplePerformanceMeasurementBase):
    """Returns the average of all times of a given key."""
    def _get_print_message(self, key):
        return '{} took an average of {}s ({} times measured)'.format(
                key, round(self.get_time_for(key), 2), self.times_measured(key))

    def get_time_for(self, key):
        all_times = super().get_time_for(key)
        return sum(all_times) / len(all_times)


class _StepLevelPerformanceMeasurement(_SumPerformanceMeasurement):
    """Specialized to measure stuff for each step type independently."""
    STEP_GIVEN = '01_GIVEN'
    STEP_WHEN = '02_WHEN'
    STEP_THEN = '03_THEN'

    def __init__(self):
        super().__init__()
        self.step_type = None

    def get_key(self, string):
        return '{}__{}'.format(string, self.step_type)

    def set_step_type(self, step):
        step_to_type = {
            Given: self.STEP_GIVEN,
            When: self.STEP_WHEN,
            Then: self.STEP_THEN,
        }

        self.step_type = step_to_type[step]


ScenarioLevelPerformanceMeasurement = _SumPerformanceMeasurement()
StepLevelPerformanceMeasurement = _StepLevelPerformanceMeasurement()
AveragePerformanceMeasurement = _AveragePerformanceMeasurement()


def measure(by: _PerformanceMeasurement, key, reset=False, export_to=None, before_measure=None, after_measure=None):
    """
    This is a decorator that allows to measure the performance of Ghengo.

    :argument: by (_PerformanceMeasurement)         - instance that measure the performance
    :argument: key (string or callable)             - a key that identifies this function for the measurement
    :argument: reset (bool)                         - should the _PerformanceMeasurement be reset after the function?
    :argument: export_to (_PerformanceMeasurement)  - export the measurement to another instance afterwards
    :argument: before_measure (callable)            - do something before measuring
    :argument: after_measure (callable)             - do something after measuring
    """
    def decorator(function):
        # simply return the normal function if we dont measure the performance
        if Settings.MEASURE_PERFORMANCE is False:
            return function

        def wrapper(*args, **kwargs):
            # get key
            if callable(key):
                clean_key = key(**kwargs)
            else:
                clean_key = key

            # call before_measure
            if before_measure:
                before_measure(by, clean_key, **kwargs)

            # measure the save the result of the function
            by.start_measure(clean_key)
            result = function(*args, **kwargs)
            by.end_measure(clean_key)

            # do something after measure
            if after_measure:
                after_measure(by, clean_key, **kwargs)

            # export to other if wanted
            if export_to:
                by.export_to_other(export_to)

            # reset if wanted
            if reset:
                by.reset()

            return result
        return wrapper
    return decorator


def before_step_measure(measure_instance: _StepLevelPerformanceMeasurement, key: str, step: Step, **kwargs):
    """The _StepLevelPerformanceMeasurement saves the current step type. This function will set the value."""
    measure_instance.set_step_type(step.get_parent_step().__class__)


def after_scenario_done(measure_instance: _PerformanceMeasurement, key: str, **kwargs):
    """After measuring a scenario, export its value to the AveragePerformanceMeasurement."""
    ScenarioLevelPerformanceMeasurement.export_to_other(AveragePerformanceMeasurement)
    ScenarioLevelPerformanceMeasurement.reset()
