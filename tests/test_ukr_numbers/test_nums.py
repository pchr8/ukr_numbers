import pytest
from ukr_numbers.nums import Numbers

def test_nums():
    n = Numbers()
    assert n.convert_to_auto(2, "тридцятий") == "другий"
    assert n.convert_to_auto(30, "тридцятий") == "тридцятий"
    assert n.convert_to_auto(3, "тридцятому") == "третьому"

def test_nums_edge():
    n = Numbers()
    # один can be a NPRO as well as NUMR, NPRO should be blacklisted
    assert n.convert_to_auto(2, "один") == "два"


#  @pytest.mark.now
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


@pytest.mark.skip("TODO: find a case where this actually happens")
def test_nums_known():
    # TODO nothing below matters till I find a word where this actually makes a differec
    #   (=  {x.normal_form for x in self.m.parse("півторма")} has more than one result)
    n = Numbers()
    assert n.convert_to_auto(2, "тридцятий", known_grammemes=["masc"]) == "друга"
