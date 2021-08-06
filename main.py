from django_meta.setup import setup_django


if __name__ == '__main__':
    setup_django('django_sample_project.apps.config.settings')

    from gherkin.compiler import GherkinToPyTestCompiler
    compiler = GherkinToPyTestCompiler()
    compiler.compile_file('django_sample_project/features/variable_reference.feature')
    compiler.export_as_file('generated_tests/')
