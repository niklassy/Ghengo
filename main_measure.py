from core.performance import AveragePerformanceMeasurement, measure, MeasureKeys
from django_meta.setup import setup_django
from settings import Settings, read_arguments

# KEEP THIS AT THE TOP OF THE FILE!!!
Settings.measure_performance = True


@measure(by=AveragePerformanceMeasurement, key=MeasureKeys.MODEL_INIT)
def _setup_nlp():
    """Sets up NLP for each iteration of performance measurement."""
    from nlp.setup import Nlp

    Nlp.setup_languages(['de', 'en'])


@measure(by=AveragePerformanceMeasurement, key=MeasureKeys.GENERATION)
def _run_ghengo():
    """Does everything the normal main method would do."""
    from gherkin.compiler import GherkinToPyTestCompiler

    compiler = GherkinToPyTestCompiler()
    compiler.compile_file(Settings.test_import_file)
    compiler.export_as_file(Settings.test_export_directory)


@measure(by=AveragePerformanceMeasurement, key=MeasureKeys.EVERYTHING)
def _main():
    """Private method that will setup NLP and run Ghengo. This is an extra function just to measure performance."""
    _setup_nlp()
    _run_ghengo()


def main():
    """The real main method that will run multiple times and collect measurement information."""

    # import this after it was defined to measure the er
    from nlp.setup import Nlp
    read_arguments()
    # this need to be executed before importing the compiler!
    setup_django(Settings.django_settings_path)

    for i in range(20):
        Nlp.reset_cache()
        _main()
        print('============== ROUND {} DONE ================='.format(i + 1))

    AveragePerformanceMeasurement.print_measurements()


if __name__ == '__main__':
    main()
