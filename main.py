from core.performance import AveragePerformanceMeasurement, SumPerformanceMeasurement
from django_meta.setup import setup_django
from nlp.setup import Nlp
from settings import Settings

if __name__ == '__main__':
    # this need to be executed before importing the compiler!
    setup_django(Settings.django_settings_path)

    from gherkin.compiler import GherkinToPyTestCompiler

    for i in range(20):
        Nlp.reset_cache()
        AveragePerformanceMeasurement.start_measure('------------------ EVERYTHING')
        AveragePerformanceMeasurement.start_measure('- 0 MODEL INIT')
        Nlp.setup_languages(['de', 'en'])
        AveragePerformanceMeasurement.end_measure('- 0 MODEL INIT')
        AveragePerformanceMeasurement.start_measure('- 1 GENERATION')
        compiler = GherkinToPyTestCompiler()
        compiler.compile_file(Settings.test_import_file)
        compiler.export_as_file(Settings.test_export_directory)
        AveragePerformanceMeasurement.end_measure('- 1 GENERATION')
        AveragePerformanceMeasurement.end_measure('------------------ EVERYTHING')
        print('============== ROUND {} DONE ================='.format(i + 1))
    AveragePerformanceMeasurement.print_all()
