from gherkin.compiler_base.line import Line


def test_line_intend():
    line = Line('123', 2)
    assert line.intend == 0
    line = Line('    123', 2)
    assert line.intend == 4


def test_line_trimmed_text():
    line = Line('123', 2)
    assert line.trimmed_text == '123'
    line = Line('    123', 2)
    assert line.trimmed_text == '123'


def test_line_is_empty():
    line = Line('123', 2)
    assert line.is_empty() is False
    line = Line('    123', 2)
    assert line.is_empty() is False
    line = Line('    ', 2)
    assert line.is_empty() is True
    line = Line('', 2)
    assert line.is_empty() is True
