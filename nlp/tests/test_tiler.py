from core.constants import Languages
from nlp.tiler import Tiler


class MockConverter:
    def __init__(self, *args, **kwargs):
        pass


class GoodConverter(MockConverter):
    def get_document_compatibility(self):
        return 1


class BadConverter(MockConverter):
    def get_document_compatibility(self):
        return .2


class AverageConverter(MockConverter):
    def get_document_compatibility(self):
        return .5


def test_tiler_best_converter():
    """Check if the tiler actually returns the best converter."""
    class CustomTiler(Tiler):
        converter_classes = [BadConverter]

    tiler = CustomTiler('Mein Text', Languages.DE, 'django_proj', 'test_case')
    assert isinstance(tiler.best_converter, BadConverter)
    tiler._best_converter = None
    tiler.converter_classes.append(AverageConverter)
    assert isinstance(tiler.best_converter, AverageConverter)
    tiler._best_converter = None
    tiler.converter_classes.append(GoodConverter)
    assert isinstance(tiler.best_converter, GoodConverter)
