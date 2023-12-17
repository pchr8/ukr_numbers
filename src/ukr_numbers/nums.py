import logging
from num2words import num2words

from pymorphy2 import MorphAnalyzer
from pymorphy2.tagset import OpencorporaTag
from pymorphy2.analyzer import Parse

from typing import Optional, Iterable
from collections import Counter

logging.basicConfig()
logger = logging.getLogger(__name__)
b = breakpoint


class Numbers:
    """Logic for inflecting numbers.

    Supports only Ukrainian language.

    Main feature:
        in:
            - a number,  like 4
                - If enabled, "-1" can be made to mean "last"
            - the inflection you need, GIVEN AS TEXT (e.g. "перший")
        out:
            the number inflected like the word given, like "червертий"

    DEALING WITH ERRORS:
        - if "останній"/last can't be inflected in the required way,
            (e.g. "перший"->"останній" is OK, "один"->??? isn't)
            None will be returned.
        - if anything goes wrong and graceful_failure is enabled,
            in the worst case scenario the number itself will be
            returned as string (2 ->'2')

    UNSUPPORTED:
        - Nouns, like 'десятка', 'десяток'
        - negative numbers, (again, except -1/last)

    FAILURE CASES:
    - mainly ones where pymorphy2 has issues, e.g.
        - пʼятьмастами, семимастами etc. (normal form detected as 'семимаст')

    """

    # Declensions with these parts of speech will be avoided always

    POS_BLACKLIST = [
        "NPRO",  # один
        "VERB",  # три
    ]
    # Will prefer Parsings with these POS
    # TODO figure a common system, if this is set POS_BLACKLIST is not needed
    POS_WHITELIST = ["ADJF", "NUMR"]
    # Grammemes that will be discarded when picking the correct-est Parse
    GRAMMEMES_TO_DISCARD = "compb"

    def __init__(
        self, negative_one_is_last: bool = True, graceful_failure: bool = False
    ):
        self.m = MorphAnalyzer(lang="uk")
        self.graceful = graceful_failure
        self.negative_one_is_last = negative_one_is_last
        self.debug_mode = False

    def fail_or_log(self, msg: str, exc=ValueError) -> None:
        if self.graceful:
            logger.warning(msg)
        else:
            raise exc(msg)

    def convert_to_auto(
        self, n: int, desc: str, known_grammemes: Optional[Iterable[str]] = None
    ) -> Optional[str]:
        """Convert the number n into a string inflected the same way as `desc`.

        For example:
            n=2, desc="тридцятьма" -> "двома"
            n=10, desc="першому" -> "десятому"
            ! n=-1, desc="першому" -> "останньому"
            !! n=-1, desc="один" -> None

        Both numerals (один) and ordinals (перший) are supported.
            Ordinals for -1 return None if -1 is enabled.
            This is the only case where None will be returned.

        If inflection should work but doesn't, graceful fallback
            to str(n) happens.

        Args:
            n (int): n an integer number
                !! n==-1 is special and means "last"
            desc (str): a Ukrainian numeral or ordinal in the needed inflection

            known_grammemes (Optional[Iterable[str]]): if `desc` can be
                understood in multiple ways, provide pymorphy2 grammemes
                that will be used to choose the correct parsing out of multiple.

                E.g. "перший" can be seen as:
                    [OpencorporaTag('ADJF,compb masc,nomn'),
                     OpencorporaTag('ADJF,compb masc,accs'),
                     OpencorporaTag('ADJF,compb masc,voct')]

                If HYPOTHETICALLY the different parsings have a different
                normal form, this can be used to pick the correct one.
                (e.g. "I want my 'перший' to be parsed as accusative").

                ~~I have not yet found any numbers where this actually matters.~~
                https://chat.openai.com/share/6d4f65d6-0bcc-40a6-bae0-dfb397f19a4f
                    Десяток!
                        ["tags: 'NOUN,inan femn,nomn' normal_form:десятка",
                         "tags: 'NOUN,inan masc,gent' normal_form:десяток"]
                But nouns are explicitly not supported.


        Returns:
            str: n as str in the hopefully correct inflection
        """

        if n < 0 if not self.negative_one_is_last else n < -1:
            raise ValueError(f"Negative numbers unsupported: {n}")

        desc = str(desc)

        # Get pymorphy2 list of parsings of desc
        parsings = self.m.parse(desc)
        # Pick the best one of them
        best = self.filter_by_grammemes(
            parsings=parsings,
            known=known_grammemes,
            pos_blacklist=Numbers.POS_BLACKLIST,
            pos_whitelist=Numbers.POS_WHITELIST,
        )

        # TODO bug? in pymorphy where singular is not annotated
        #   we add it ourselves
        best = self._add_sing_to_parse(best)

        parsing = best
        pos = parsing.tag.POS
        grammemes = parsing.tag.grammemes
        if "UNKN" in grammemes:
            self.fail_or_log(
                f"Can't do {n} {desc} {known_grammemes} because parsing is unknown: {parsing}"
            )
            return str(n)
        if "LATN" in grammemes:
            self.fail_or_log(f"Currently only Ukrainian is supported, not latin {desc}")
            return str(n)
        if "NOUN" in grammemes:
            self.fail_or_log(f"Nouns (~десяток) are unsupported. {desc=}, {grammemes=}")
            return str(n)

        if "NUMB" in grammemes:
            # If we got a number like '2', return the n as-is
            return str(n)

        if "ADJF" in grammemes:
            # We're dealing with an ordinal of some kind
            # тридцятий
            if n == -1:
                base_form = "останній"
            else:
                base_form = self.to_ordinal(n)
        elif "NUMR" in grammemes:
            # тридцять
            if n == -1 and self.negative_one_is_last:
                return None
            else:
                # TODO in this case we can do num2words(.., case="accusative")
                base_form = self.to_number(n)
        else:
            self.fail_or_log(
                f"Neither ADJF nor NUMR in grammemes {grammemes} for {parsing=} of {n=} {desc=} {known_grammemes=}"
            )
            return str(n)

        # filtering for VERB (три) etc. currently happening as part of the blacklist
        base_parsings = self.m.parse(base_form)
        base_parsed = self.filter_by_grammemes(
            parsings=base_parsings,
            pos_blacklist=Numbers.POS_BLACKLIST,
            pos_whitelist=Numbers.POS_WHITELIST,
        )
        base_parsed = self._add_sing_to_parse(base_parsed)

        clean_grammemes = self._remove_bad_grammemes(
            grammemes, bad_grammemes=Numbers.GRAMMEMES_TO_DISCARD
        )
        #  base_inflected = base_parsed.inflect(clean_grammemes)
        base_inflected = self._inflect(base_parsed, clean_grammemes)
        if not base_inflected:
            logger.warning(
                f"Something went wrong when inflecting {base_parsed} -> {clean_grammemes} to match {desc}, falling back"
            )
            if self.debug_mode:
                b()
            return str(n)
        res = base_inflected.word
        return res

    @staticmethod
    def to_number(n: int) -> str:
        word = num2words(n, lang="uk")
        # чертвертий
        return word

    @staticmethod
    def to_ordinal(n: int) -> str:
        word = num2words(n, lang="uk", to="ordinal")
        # чертвертий
        return word

    @staticmethod
    def filter_by_grammemes(
        parsings: list,
        known: Optional[Iterable[str]] = None,
        pos_blacklist=None,
        pos_whitelist=None,
    ):
        """filter_by_grammemes.

        Very often you can't differentiate masc/neut and case
         m.parse("першому")
            [Parse(word='першому', tag=OpencorporaTag('ADJF,compb masc,datv'), normal_form='перший', score=1.0, methods_stack=((DictionaryAnalyzer(), 'першому', 76, 2),)),
             Parse(word='першому', tag=OpencorporaTag('ADJF,compb masc,loct'), normal_form='перший', score=1.0, methods_stack=((DictionaryAnalyzer(), 'першому', 76, 7),)),
             Parse(word='першому', tag=OpencorporaTag('ADJF,compb neut,datv'), normal_form='перший', score=1.0, methods_stack=((DictionaryAnalyzer(), 'першому', 76, 18),)),
             Parse(word='першому', tag=OpencorporaTag('ADJF,compb neut,loct'), normal_form='перший', score=1.0, methods_stack=((DictionaryAnalyzer(), 'першому', 76, 22),))]

        BUT that doesn't seem to matter anyway, because I can't find any number where it changes the normal form
            (=  {x.normal_form for x in self.m.parse("півторма")} has more than one result)
        """
        # If we have a whitelist and we have parsings matching it, restrict
        #   the list to them.
        if pos_whitelist:
            whitelist_parsings = [p for p in parsings if p.tag.POS in pos_whitelist]
            if whitelist_parsings:
                parsings = whitelist_parsings

        # If the list of parsings has known-bad POSs, remove them
        if pos_blacklist:
            parsings = [p for p in parsings if p.tag.POS not in pos_blacklist]

        # If no other info, we just return the first remaining parsing
        #   and hope for the best
        if not known:
            return parsings[0]

        # Otherwise if we have additional info, pick the parsing
        #   that has the most intersections with the known grammemes
        known = set(known)

        sim = Counter()
        for i, p in enumerate(parsings):
            for k in known:
                for g in p.tag.grammemes:
                    if k == g:
                        sim[i] += 1
        most_c = sim.most_common(1)
        if not most_c:
            return parsings[0]

        # if it's a tie, we pick the first
        best_n = most_c[0][0]

        best = parsings[best_n]
        return best

    @staticmethod
    def _remove_bad_grammemes(grammemes: set | frozenset, bad_grammemes):
        """
        Remove problematic grammemes from list.

        - compb - ~comp - [LT2OpenCorpora/lt2opencorpora/mapping.csv at master · dchaplinsky/LT2OpenCorpora](https://github.com/dchaplinsky/LT2OpenCorpora/blob/master/lt2opencorpora/mapping.csv)

        """
        new_set = set(grammemes)
        new_set.discard("compb")
        return new_set

    @staticmethod
    def _inflect(parse: Parse, new_grammemes: set | frozenset) -> Parse:
        """Sometimes inflecting with the entire batch fails, but one by one
        works. This chains the grammemes for one inflection at a time."""
        new_parse = parse
        for g in new_grammemes:
            if new_parse.inflect({g}):
                new_parse = new_parse.inflect({g})
            else:
                continue
        return new_parse

    @staticmethod
    def _make_agree_with_number(parse: Parse, n: int) -> Parse:
        grams = parse.tag.numeral_agreement_grammemes(n)
        new_parse = Numbers._inflect(parse=parse, new_grammemes=grams)
        return new_parse

    @staticmethod
    def _add_sing_to_parse(parse: Parse) -> Parse:
        """
        pymorphy sometimes doesn't add singular for ukrainian
        (and fails when needs to inflect it to plural etc.)

        this creates a new Parse with that added.
        """
        if parse.tag.number is not None:
            return parse

        new_tag_str = str(parse.tag)
        new_tag_str += ",sing"
        new_tag = parse._morph.TagClass(tag=new_tag_str)
        new_best_parse = Parse(
            word=parse.word,
            tag=new_tag,
            normal_form=parse.normal_form,
            score=parse.score,
            methods_stack=parse.methods_stack,
        )
        new_best_parse._morph = parse._morph
        return new_best_parse
