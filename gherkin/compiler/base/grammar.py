from gherkin.compiler.base.exception import RuleNotFulfilled, SequenceEnded, GrammarNotUsed, GrammarInvalid, \
    SequenceNotFinished
from gherkin.compiler.base.wrapper import RuleAlias, RuleToken


class Grammar(object):
    """
    A grammar represents a combination of rules that has a special criterion to recognize it with.
    This criterion is a RuleAlias. If there is an error while validating a grammar object,
    it will check:
        - am i optional? - if yes, continue normally

        - did the error occur AFTER the defined RuleAlias was validated?
            -> if yes, it means that the input `tries` to create this Grammar
        - was the error raised by that exact RuleAlias?
            -> if yes, it means again that the input `tried` to create this Grammar

        => if either of those cases are true, this will raise a GrammarInvalid exception.

    This is useful to differentiate between:
        - is the grammar optional?
        - did the input actually try to create this Grammar?
        - should the validation continue?

    Grammar objects separate Rules from each other and isolate each "Area" of grammar. If
    a rule raises an error, the grammar catches and handles it.
    """
    name = None
    rule = None
    criterion_rule_alias: RuleAlias = None

    class GrammarPlaceholder(object):
        def __init__(self, **kwargs):
            pass

    ast_object_cls = GrammarPlaceholder

    def __init__(self):
        if self.get_rule() is None:
            raise ValueError('You must provide a rule')

        from gherkin.compiler.base.rule import Chain
        if not isinstance(self.get_rule(), Chain):
            raise ValueError('You must only use Chain on Grammar objects as its rule.')

        if self.criterion_rule_alias is not None and not isinstance(self.criterion_rule_alias, RuleAlias):
            raise ValueError('You must either use None or a RuleAlias instance for criterion_rule_alias.')

        self.validated_sequence = None

    def get_rule(self):
        return self.rule

    def get_name(self):
        """
        Returns the name of the grammar. By default it uses the name of the token class in the criterion_rule_alias
        """
        return self.criterion_rule_alias.token_cls.__name__ if not self.name else self.name

    def get_grammar_criterion(self) -> RuleAlias:
        """
        Returns the criterion that defines this grammar/ that makes this grammar recognizable.
        """
        return self.criterion_rule_alias

    def used_by_sequence_area(self, sequence, start_index, end_index):
        """Checks if this grammar is used in a given area in a sequence of RuleTokens."""
        criterion = self.get_grammar_criterion()

        if not criterion:
            return False

        non_committed = sequence[start_index:end_index]

        return criterion in [t.rule_alias for t in non_committed]

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
            if not self.used_by_sequence_area(sequence, index, e.sequence_index):
                raise GrammarNotUsed(
                    str(e), rule_alias=e.rule_alias, sequence_index=e.sequence_index, rule=e.rule, grammar=self)

            raise GrammarInvalid('Invalid syntax for {} - {}'.format(self.get_name(), str(e)), grammar=self)

    def validate_sequence(self, sequence: [RuleToken]):
        """
        The entrypoint to the validation. Call this function to start the validation of a sequence.

        :raises SequenceNotFinished - all rules were fulfilled, but there are still elements in the sequence that were
                                    not validated.
        :raises GrammarInvalid  - The grammar was used but is not valid. It is also thrown when the grammar that
                                used this method is not used in the sequence.
        :raises GrammarNotUsed  - This grammar could not be identified and is not used in the sequence. This is only
                                risen if the top level Grammar is not recognized.
        """
        assert all([isinstance(el, RuleToken) for el in sequence]), 'Every entry in the passed sequence must be of ' \
                                                                    'class "RuleToken"'

        result_index = self._validate_sequence(sequence, 0)

        if result_index < len(sequence):
            raise SequenceNotFinished()

        self.validated_sequence = sequence

        return result_index

    def get_ast_objects_kwargs(self, rule_output):
        """Can be used to modify what is passed to the ast_object __init__"""
        return {}

    def get_rule_tree(self, sequence, index):
        """Returns the tree that is returned by self.get_rule"""
        return self.get_rule().sequence_to_object(sequence, index)

    def get_tree_object(self, sequence, index):
        """Returns an object of the ast_object_cls"""
        return self.ast_object_cls(**self.get_ast_objects_kwargs(self.get_rule_tree(sequence, index)))

    def prepare_object(self, rule_output, obj):
        """Can be used to modify the object before it is returned by `convert`."""
        return obj

    def sequence_to_object(self, sequence, index=0):
        """
        Returns an object that represents this grammar. By default it will create an instance of `ast_object_cls`,
        add kwargs and return it. The object can be used by the caller of this function.
        """
        tree_for_rule = self.get_rule_tree(sequence, index)
        kwargs = self.get_ast_objects_kwargs(tree_for_rule)
        obj = self.ast_object_cls(**kwargs)
        return self.prepare_object(tree_for_rule, obj)

    def convert(self, sequence):
        """Converts a given sequence into an object that can be used as an ast."""
        self.validate_sequence(sequence)

        return self.sequence_to_object(sequence, 0)
