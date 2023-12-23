import logging
from num2words import num2words

from typing import Optional, Iterable
from dataclasses import dataclass
from enum import Enum

from pprint import pprint, pformat


logging.basicConfig()
logger = logging.getLogger(__name__)
b = breakpoint


class NumSuffixes(Enum):
    #  СТО = 2
    ТИСЯЧА = 3
    МІЛЬЙОН = 6
    МІЛЬЯРД = 9

    @classmethod
    def values(cls):
        return cls._value2member_map_


@dataclass
class NumberMetadata:
    """Metadata about a specific number/transformation/...

    In comments,
        - 'source number' is the int we're inflecting
        - 'target' refers to the target declension (description or str)
    """

    ######
    ## SOURCE NR  ATTRS
    ######

    # number to inflect without sign, or None if 'last'
    n: Optional[int]
    # special case 'last', if True `n` is ignored
    is_last: bool = False
    # sign of number to inflect
    is_negative: bool = False

    ######
    ## SOURCE NR GRAMMAR
    ######

    # Normal form of the natural language of the number, ordinal or cardinal
    #   e.g. перший/другий or один/сто
    #   IF ORDINAL CAN BE "LAST" (=останній!)
    # Automatically sets base_form and beginning_of_number
    _complete_base_form: str = None

    # Last word of base form
    #   (e.g. сто тридцять вісім -> вісім)
    base_form: str = None
    # All words of complete base form except the last word.
    #   (e.g. сто тридцять вісім -> сто тридцять)
    beginning_of_number: str = ""

    ######
    ## SOURCE NUMBER DERIVED ATTRS
    ######
    num_zeroes_at_the_end: int = None

    # if the number as ordinal nominative in Ukrainian has more than one word
    # yes: 100_000 (сто тисяч), no: 100, 4
    is_multi_word: bool = None

    ## TARGET ATTRS
    # if False -> it's cardinal
    is_ordinal: Optional[bool] = None

    ######
    ## PROPERTIES / fields
    ######

    @property
    def complete_base_form(self):
        return self._complete_base_form

    @complete_base_form.setter
    def complete_base_form(self, value: str):
        self._complete_base_form = value
        self.beginning_of_number, self.base_form = self._get_multiword_parts(value)

    ######
    ## METHODS
    ######

    @classmethod
    def from_number(cls, n: Optional[int]):
        if n is None:
            return cls(n=n, is_last=True)
        if n > 0:
            res = cls(n=n)
        else:
            res = cls(n=-n, is_negative=True)
        res._set_num_attrs()
        return res

    def _set_num_attrs(self):
            """Sets metadata based on self.n"""
            self.num_zeroes_at_the_end = self._calc_num_zeroes_at_the_end(self.n)
            self.is_multi_word = len(num2words(self.n, lang="uk").split(" ")) > 1

    @staticmethod
    def _get_multiword_parts(base_form: str) -> tuple[str, str]:
        """Splits base_form into two parts:
            beginning_of_number = all words except the last one
            new base_form = the last word.

        If base_form is one word, beginning_of_number is empty.
        """
        parts = base_form.split(" ")

        #  beginning_of_number = " ".join(number_parts[:-1])
        #  base_form = parts[-1]
        return " ".join(parts[:-1]), parts[-1]

    @staticmethod
    def _calc_num_zeroes_at_the_end(n: int):
        s = str(n)
        return len(s) - len(s.rstrip("0"))

