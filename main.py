from django_meta.setup import setup_django
from settings import Settings, read_arguments


def main():
    # this need to be executed before importing the compiler!
    read_arguments()
    setup_django(Settings.django_settings_path)

    from gherkin.compiler import GherkinToPyTestCompiler

    compiler = GherkinToPyTestCompiler()
    compiler.compile_file(Settings.test_import_file)
    compiler.export_as_file(Settings.test_export_directory)


if __name__ == '__main__':
    main()
