from gherkin.compiler_base.exception import RuleNotFulfilled, SequenceEnded, GrammarNotUsed, GrammarInvalid
from gherkin.compiler_base.mixin import IndentMixin
from gherkin.compiler_base.recursive import RecursiveValidationBase
from gherkin.compiler_base.rule import Rule
from gherkin.compiler_base.terminal import TerminalSymbol


class Grammar(IndentMixin, RecursiveValidationBase):
    name = None
    rule = None
    criterion_terminal_symbol: TerminalSymbol = None
    convert_cls = None

    def __init__(self):
        super().__init__()

        if self.get_rule() is None:
            raise ValueError('You must provide a rule')

        from gherkin.compiler_base.rule import Chain
        if not isinstance(self.get_rule(), Chain):
            raise ValueError('You must only use Chain on Grammar objects as its rule.')

        criterion_terminal_symbol = self.criterion_terminal_symbol
        if criterion_terminal_symbol is not None and not isinstance(criterion_terminal_symbol, TerminalSymbol):
            raise ValueError('You must either use None or a RuleAlias instance for criterion_terminal_symbol.')

        self.validated_sequence = None

        self.get_rule().set_parent(self)

    @classmethod
    def get_minimal_sequence(cls):
        return []

    def get_next_valid_tokens(self):
        tokens = self.get_rule().get_next_valid_tokens()
        if not isinstance(tokens, list):
            tokens = [tokens]
        return tokens

    def get_rule(self) -> Rule:
        """Returns the rule of this grammar."""
        return self.rule

    def get_name(self):
        """
        Returns the name of the grammar. By default it uses the name of the token class in the criterion_terminal_symbol
        """
        return self.criterion_terminal_symbol.token_cls.__name__.replace('Token', '') if not self.name else self.name

    def get_grammar_criterion(self) -> TerminalSymbol:
        """
        Returns the criterion that defines this grammar/ that makes this grammar recognizable.
        """
        return self.criterion_terminal_symbol

    def used_by_sequence_area(self, sequence, start_index, end_index):
        """Checks if this grammar is used in a given area in a sequence of RuleTokens."""
        criterion = self.get_grammar_criterion()

        if not criterion:
            return False

        non_committed = sequence[start_index:end_index]

        return criterion in [t.terminal_symbol for t in non_committed]

    def get_next_pointer_index(self, child, sequence, current_index) -> int:
        return self.get_rule().get_next_pointer_index(child, sequence, current_index)

    def _validate_sequence(self, sequence, index):
        """
        Validates the given sequence. If this is called by a parent, no index should be passed.
        It will call Rules that will call this method recursively.

        :raises GrammarInvalid

        :arg sequence - list of RuleTokens - they represent all tokens from an input text
        :arg index (default 0) - the current index of validation in the sequence

        :return: current index in sequence
        """
        try:
            # noinspection PyProtectedMember
            return self.get_rule()._validate_sequence(sequence, index)
        except (RuleNotFulfilled, SequenceEnded) as e:
            next_valid_tokens = e.suggested_tokens
            valid_keywords = []

            for t in next_valid_tokens:
                valid_keywords += t.get_keywords()
            try:
                error_token = sequence[e.sequence_index]
                message = 'Expected one of {}. Got {} instead. {}'.format(
                    ', '.join(valid_keywords), error_token.get_text(), error_token.get_place_to_search()
                )
            except IndexError:
                message = str(e)

            if not self.used_by_sequence_area(sequence, index, e.sequence_index):
                raise GrammarNotUsed(
                    message, terminal_symbol=e.terminal_symbol, sequence_index=e.sequence_index, rule=e.rule, grammar=self)

            raise GrammarInvalid(message, grammar=self, suggested_tokens=e.suggested_tokens)

    def validate_sequence(self, sequence, index=0):
        result_index = super().validate_sequence(sequence, 0)
        self.validated_sequence = sequence
        return result_index

    def get_convert_kwargs(self, rule_output):
        """Can be used to modify what is passed to the convert_cls __init__"""
        return {}

    def get_rule_sequence_to_object(self, sequence, index):
        """Returns the tree that is returned by self.get_rule"""
        return self.get_rule().sequence_to_object(sequence, index)

    def prepare_converted_object(self, rule_convert_obj, grammar_obj):
        """Can be used to modify the object before it is returned by `convert`."""
        return grammar_obj

    def sequence_to_object(self, sequence, index=0):
        """
        Returns an object that represents this grammar. By default it will create an instance of `ast_object_cls`,
        add kwargs and return it. The object can be used by the caller of this function.
        """
        if self.convert_cls is None:
            raise NotImplementedError('You must provide a class that this Grammar converts into.')

        object_of_rule = self.get_rule_sequence_to_object(sequence, index)
        kwargs = self.get_convert_kwargs(object_of_rule)
        obj = self.convert_cls(**kwargs)

        return self.prepare_converted_object(object_of_rule, obj)
