import logging

from num2words import num2words

from pymorphy2 import MorphAnalyzer
from pymorphy2.tagset import OpencorporaTag
from pymorphy2.analyzer import Parse

from collections import Counter
from dataclasses import dataclass
from enum import Enum

from ukr_numbers.data_structures import NumSuffixes, NumberMetadata

from typing import Optional, Iterable

from pprint import pprint, pformat


logging.basicConfig()
logger = logging.getLogger(__name__)
b = breakpoint


class Numbers:
    """Logic for inflecting numbers in Ukrainian.

    Main feature:
        in:
            - a number, like 4 (or -1 for negatives if enabled)
            - the inflection you need, GIVEN AS TEXT (e.g. "перший")
                (=inflect any simple number to the inflection you want)
        out:
            the number inflected like the word given, like
                - "червертий"
                - "мінус чотирнадцятисячному"

    DEALING WITH ERRORS:
        - if "останній"/last can't be inflected in the required way,
            (e.g. "перший"->"останній" is OK, "один"->??? isn't)
            None will be returned.
        - worst case scenario the number will be returned as string (2 ->'2')

    UNSUPPORTED:
        - multi-word numbers have a high chance of being wrong
        - Nouns, like 'десятка', 'десяток'
        - Fractions ('три з половиною тисячі')
        - Nums larger than a trillion

    FAIL CASES:
        - два мільйонА/мільйонИ - TODO not sure what is right
        - complex cases from https://ukr-lifehacks.ed-era.com/rozdil-9/vidminuvannya_chuslivnukiv (TODO document)
            - esp. ДВОМА мільйонами
    """

    # Declensions with these parts of speech will be avoided always

    POS_BLACKLIST = [
        "NPRO",  # один
        "VERB",  # три
    ]
    # Will prefer Parsings with these POS
    # TODO with this can I remove POS_BLACKLIST?
    POS_WHITELIST = ["ADJF", "NUMR"]

    # Grammemes that will be discarded when picking the correct-est Parse
    GRAMMEMES_TO_DISCARD = "compb"

    def __init__(
        self,
        negative_one_is_last: bool = True,
        graceful_failure: bool = False,
        quiet=False,
    ):
        """

        Args:
            negative_one_is_last (bool): if True, will interpret -1 as 'last'
                but disable support for negative numbers
            graceful_failure (bool): recover from errors where possible by
                returning str(int) and logging instead of raising exception
            quiet: whether recoverable exceptions should be logged
                as warning or debugs
        """
        self.negative_one_is_last = negative_one_is_last

        self.m = MorphAnalyzer(lang="uk")

        self.graceful = graceful_failure
        self.quiet = quiet

        # TODO remove in 'prod' :P
        # If debug_mode is True, self.b() will drop into a pdb shell
        self.debug_mode = True
        self.b = b if self.debug_mode else int

    def _fail_or_log(self, msg: str, exc=ValueError) -> None:
        """if graceful, log instead of raising. If quiet, use loglevel debug instead of warning."""
        if self.graceful:
            if self.quiet:
                logger.debug(msg)
            else:
                logger.warning(msg)
        else:
            raise exc(msg)

    def convert_to_auto(
        self,
        n: int,
        target_inflection: str,
        #  known_grammemes: Optional[Iterable[str]] = None,
    ) -> Optional[str]:
        """Convert the number n into a string inflected the same way as `target_inflection`.

        For example:
            n=2, ti="тридцятьма" -> "двома"
            n=10, ti="першому" -> "десятому"
            ! n=-1, ti="першому" -> "останньому"
            !! n=-1, ti="один" -> None

        Both numerals (один) and ordinals (перший) are supported.
            Ordinals for -1 return None if -1 is enabled.
            This is the only case where None will be returned.

        Args:
            n (int): n an integer number
                !! n==-1 is special and means "last"
            ti (str): a Ukrainian numeral or ordinal in the needed inflection

        Returns:
            str: n as str in the hopefully correct inflection
        """

        meta = NumberMetadata.from_number(
            n=None if self.negative_one_is_last and n == -1 else n
        )

        if meta.n and meta.n > 1_000_000_000_000:
            raise ValueError(f"Nums larger than a trillion unsupported: {n}")
        if meta.is_multi_word:
            logger.warning(
                f"Support for multi-word numbers ({n}) is bad, errors are likely to happen, you're warned."
            )

        target_inflection = str(target_inflection)

        if target_inflection.isdigit():
            return str(n)

        if len(target_inflection.split(" ")) > 1:
            # same: тисяча, мільйон are parsed as nouns
            raise ValueError(
                f"Please use a simple (<10, one-word) number for your target declension."
            )

        # Get pymorphy2 list of parsings of target_inflection
        parsings_target = self.m.parse(target_inflection)
        logger.debug(f"Target parsings options: {pformat(parsings_target)}")

        # Pick the best one
        t_parse = self.filter_by_grammemes(
            parsings=parsings_target,
            #  known=known_grammemes,
            pos_blacklist=Numbers.POS_BLACKLIST,
            pos_whitelist=Numbers.POS_WHITELIST,
        )
        logger.debug(f"Best target parsing: {t_parse}")

        t_pos = t_parse.tag.POS
        t_grammemes = t_parse.tag.grammemes

        ######
        # EASY CASES
        ######

        # Deal with cases where target_inflection is imperfect
        grams_map = {
            "NUMB": None,
            "UNKNOWN": f"Can't do {n}->{target_inflection}  because target parsing is unknown: {t_parse}",
            "LATN": f"Currently only Ukrainian is supported, not latin {target_inflection}",
            "NOUN": f"Nouns (~десяток) are unsupported. {target_inflection=}, {t_grammemes=}",
        }
        for grm, msg in grams_map.items():
            if grm in t_grammemes:
                #  self._fail_or_log(msg.format(**locals()))  # format string
                self._fail_or_log(msg)  # format string
                return str(n)

        ######
        # GET BASE FORM (str, uninflected) OF SOURCE NUMBER
        ######

        if "ADJF" in t_grammemes:
            # We're dealing with an ordinal of some kind
            # тридцятий
            logger.debug(
                f"{target_inflection}'s an ordinal, because {t_parse} is ADJF: {t_parse=}"
            )
            meta.is_ordinal = True

            if meta.is_last:
                meta.complete_base_form = "останній"
            else:
                meta.complete_base_form = self.to_ordinal(meta.n)

        elif "NUMR" in t_grammemes:
            # cardinal numeral
            # тридцять
            logger.debug(
                f"{target_inflection}'s a cardinal nr, because {t_parse} is NUMR: {t_parse=}"
            )
            meta.is_ordinal = False

            # 'last' w/ cardinal doesn't exist
            if meta.is_last:
                logger.debug(
                    f"Number is 'last' and target is a cardinal, inflection impossible. (перший->останній, один->???)"
                )
                return None

            # NB this automatically sets meta.beginning_of_number
            # "сто тисяч вісім" -> bon = "сто тисяч", base_form = "вісім"
            meta.complete_base_form = self.to_number(meta.n)

            logger.debug(f"Got NUMR ({t_grammemes}) for {t_parse} ({n=})")

        else:
            self._fail_or_log(
                f"Neither ADJF nor NUMR in grammemes {t_grammemes} for {t_parse=} of {n=} {target_inflection=} "
            )
            return str(n)

        ######
        # INFLECT BASE FORM
        ######
        logger.debug(f"Base form: {meta.base_form}")
        logger.debug(meta)

        word_end_form = meta.base_form

        # filtering for VERB (три) etc. currently happening as part of the blacklist
        bf_parsings = self.m.parse(word_end_form)

        bf_parse = self.filter_by_grammemes(
            parsings=bf_parsings,
            pos_blacklist=Numbers.POS_BLACKLIST,
            pos_whitelist=Numbers.POS_WHITELIST,
            #  known=known,
        )

        clean_t_grammemes = self._remove_bad_grammemes(
            t_grammemes, bad_grammemes=Numbers.GRAMMEMES_TO_DISCARD
        )

        bf_inflected = self._inflect(bf_parse, clean_t_grammemes)

        if not meta.is_ordinal and meta.num_zeroes_at_the_end in NumSuffixes.values():
            # If number is thousand/million/... (suffixes) make sure it agrees
            #   with however many millions there are.
            #   один мільйоН, два мільйонА(и?)
            num_before_zeroes = int(str(meta.n)[-meta.num_zeroes_at_the_end - 1])
            hr_pref_inflected = self._make_agree_with_number(
                bf_inflected, num_before_zeroes
            )
            bf_inflected = hr_pref_inflected

        if not bf_inflected:
            logger.warning(
                f"Something went wrong when inflecting {bf_parse} -> {clean_t_grammemes} to match {target_inflection}, falling back"
            )
            self.b()
            return str(n)

        res = meta.beginning_of_number
        if res:
            res += " "
        res += bf_inflected.word
        res_fixed = self.fix_edge_cases(inflected_num=res, meta=meta)
        #  self.b()

        return res_fixed

    @staticmethod
    def fix_edge_cases(inflected_num: str, meta: NumberMetadata):
        # Write without spaces ordinals ending in certain suffixes
        """
        https://dyskurs.net/skladni-chyslivnyky/ каже, що разом пишемо...
        > складні порядкові числівники, останнім компонентом яких є -сотий, -тисячний, -мільйонний, -мільярдний: дев’ятисо́тий, трьохсо́тий; двохтúсячний, десятитúсячний, п’ятсоттридцятити́сячний; чотирьохмільйо́нний, п’ятдесятимільйóнний, шістдесятип’ятимільйо́нний; семимілья́рдний, трьохмілья́рдний.
        """
        if meta.is_ordinal:
            # num2word seems to take care of this except for one hundred
            # TODO - bug report to them if my understanding of the rule is right?
            if (
                meta.num_zeroes_at_the_end
                == 2
                #  or meta.num_zeroes_at_the_end in NumSuffixes.values()
            ):
                inflected_num = inflected_num.replace(" ", "")

        # Handle negative numbers
        if meta.is_negative:
            inflected_num = f"мінус {inflected_num}"
        return inflected_num

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
    ) -> Parse:
        """Given a list of parsings, pick the 'best' one.

        Will try to pick a parsings from the whitelist POS, to not pick
        any from blacklist, and to prefer ones where the grammemes
        match the ones passed in `known`.

        Use case - multiple interpretations of your word but you know
        something about its morphology.

        E.g. тисячі can be
            - "немає однієї тисячі гривень" (femn, genitive, SINGULAR)
            -"в мене три тисячі собак" (masc, plur, masc)

        Args:
            parsings (list): list of pymorphy2 Parse objects from which to pick
            known (Optional[Iterable[str]]): list of grammemes should be in the parsing
            pos_blacklist: POS of this type won't be picked if possible
            pos_whitelist: POS of this type will be picked if possible.

        Returns:
            Parse:
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
        works. This chains the grammemes for one inflection at a time.

        This is a workaround for a pymorphy bug:
        https://github.com/pymorphy2/pymorphy2/issues/169
        """
        new_parse = parse
        for g in new_grammemes:
            if new_parse.inflect({g}):
                new_parse = new_parse.inflect({g})
            else:
                continue
        return new_parse

    @staticmethod
    def _make_agree_with_number(parse: Parse, n: int) -> Parse:
        """Inflect `parse` to agree in number with `n`.
        (Like singular/plural, except 2-4 and5 5+ are separate in Ukrainian)

        Fix for pymorphy bug its function for this.
        Pymorphy bug: https://github.com/pymorphy2/pymorphy2/issues/169


        Args:
            parse (Parse): parse object to inflect to match number
            n (int): n number to agree on.

        Returns:
            Parse:
        """
        grams = parse.tag.numeral_agreement_grammemes(n)
        new_parse = Numbers._inflect(parse=parse, new_grammemes=grams)
        return new_parse

    @staticmethod
    def _add_sing_to_parse(parse: Parse) -> Parse:
        """
        pymorphy sometimes doesn't add singular for ukrainian
        (and fails when needs to inflect it to plural etc.)

        Bug: https://github.com/pymorphy2/pymorphy2/issues/169

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
