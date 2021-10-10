from django_meta.setup import setup_django
from settings import Settings


def main():
    # this need to be executed before importing the compiler!
    setup_django(Settings.DJANGO_SETTINGS_PATH, print_warning=True)

    from gherkin.compiler import GherkinToPyTestCompiler

    compiler = GherkinToPyTestCompiler()
    compiler.compile_file(Settings.TEST_IMPORT_FILE)
    compiler.export_as_file(Settings.TEST_EXPORT_DIRECTORY)


if __name__ == '__main__':
    main()
