from django_meta.setup import setup_django
from settings import Settings

if __name__ == '__main__':
    # this need to be executed before importing the compiler!
    setup_django(Settings.django_settings_path)

    from gherkin.compiler import GherkinToPyTestCompiler
    compiler = GherkinToPyTestCompiler()
    compiler.compile_file(Settings.test_import_file)
    compiler.export_as_file(Settings.test_export_directory)
