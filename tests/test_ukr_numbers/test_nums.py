import pytest
import logging
from ukr_numbers.nums import Numbers, NumberMetadata


def test_nums():
    n = Numbers()
    assert n.convert_to_auto(2, "тридцятий") == "другий"
    assert n.convert_to_auto(30, "тридцятий") == "тридцятий"
    assert n.convert_to_auto(3, "тридцятому") == "третьому"


def test_nums_edge():
    n = Numbers()
    # один can be a NPRO as well as NUMR, NPRO should be blacklisted
    assert n.convert_to_auto(2, "один") == "два"


def test_multiple_digits():
    n = Numbers()
    ins = [
        100,
        12000,
        13833,
        2_000_000,
    ]
    descs = [
        #  "один",
        #  "першому",
        #  "трьох",
        "трьома",
        "трьома",
        "трьома",
        "трьома",
    ]
    exp = [
        "сто",
        "дванадцятитисячному",
        "тринадцять тисяч вісімсот тридцять трьох",
        "два тисячами",
    ]

    #  """
    ress = list()
    for i, d, e in zip(ins, descs, exp):
        #  assert  n.convert_to_auto(i, d)==e
        ress.append(n.convert_to_auto(i, d))
    logging.error(ress)
    #  """


def test_nums_fails():
    n = Numbers(graceful_failure=False)
    with pytest.raises(ValueError):
        assert n.convert_to_auto(2, "пʼятьмастами")
    with pytest.raises(ValueError):
        assert n.convert_to_auto(2, "whatever")
    with pytest.raises(ValueError):
        assert n.convert_to_auto(2, "десяток")
    with pytest.raises(ValueError):
        assert n.convert_to_auto(2, "десятка")

    assert n.convert_to_auto(2, 232) == "2"

    n = Numbers(graceful_failure=True)
    assert n.convert_to_auto(2, "пʼятьмастами") == "2"
    assert n.convert_to_auto(2, "whatever") == "2"
    assert n.convert_to_auto(2, "десяток") == "2"
    assert n.convert_to_auto(2, "десятка") == "2"

    assert n.convert_to_auto(2, 232) == "2"


def test_nums_two():
    n = Numbers(graceful_failure=False)
    assert n.convert_to_auto(22, "другий") == "двадцять другий"
    assert n.convert_to_auto(22, "два") == "двадцять два"


@pytest.mark.skip(reason="two-digit support missing")
def test_nums_known_bad():
    n = Numbers(graceful_failure=False)
    assert n.convert_to_auto(23, "два") == "двадцять три"
    assert n.convert_to_auto(28, "два") == "двадцять восьмий"


@pytest.mark.skip("TODO: find a case where this actually happens")
def test_nums_known():
    # TODO nothing below matters till I find a word where this actually makes a differec
    #   (=  {x.normal_form for x in self.m.parse("півторма")} has more than one result)
    n = Numbers()
    assert n.convert_to_auto(2, "тридцятий", known_grammemes=["masc"]) == "друга"


def test_ds():
    md = NumberMetadata.from_number(3)
    assert md.n==3
    assert md.num_zeroes_at_the_end==0
    assert md.is_negative is False
    assert md.is_multi_word is False

    assert NumberMetadata.from_number(None).is_last is True
    large = NumberMetadata.from_number(100_000)
    assert large.is_multi_word is True

    # test base form multipart setter
    large.complete_base_form = "сто тисяч"
    assert large.beginning_of_number=="сто"
    assert large.base_form=="тисяч"


