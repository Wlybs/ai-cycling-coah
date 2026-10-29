"""lit_search 纯函数测试（不联网）。"""
from scripts.lit_search import _clean, _first_author, _fmt_pubmed


class TestClean:
    def test_keeps_comparison_operators(self):
        # 2026-10-28 回归：旧正则 <[^>]+> 把 "< 1.1), moderate (≥ 1.1 but < 1.2) or high (≥" 整段当标签删掉
        s = "classified as low (< 1.1), moderate (≥ 1.1 but < 1.2) or high (≥ 1.2)."
        assert _clean(s) == s

    def test_keeps_bare_inequalities(self):
        s = "(SMALL, <70 kg body mass, n = 9) or (LARGE, >70 kg body mass, n = 6)"
        assert _clean(s) == s

    def test_strips_markup_tags(self):
        assert _clean("<i>V</i>O<sub>2max</sub> rose") == "V O 2max rose"

    def test_unescapes_entities_then_strips_tags(self):
        assert _clean("&lt;sup&gt;13&lt;/sup&gt;C-glucose") == "13 C-glucose"

    def test_none_is_empty(self):
        assert _clean(None) == ""


class TestFirstAuthor:
    def test_single_author(self):
        assert _first_author("Jeukendrup A.") == "Jeukendrup A."

    def test_multiple_authors(self):
        assert _first_author("Smyth B, Maunder E, Meyler S") == "Smyth B et al."

    def test_empty(self):
        assert _first_author("") == "?"


class TestFmtPubmed:
    def test_line_has_ids_and_types(self):
        d = {
            "uid": "35511416", "pubdate": "2022 Sep",
            "authors": [{"name": "Smyth B"}, {"name": "Maunder E"}],
            "title": "Decoupling of Internal and External Workload During a Marathon.",
            "source": "Sports Med", "volume": "52", "issue": "9", "pages": "2283-2295",
            "articleids": [{"idtype": "doi", "value": "10.1007/s40279-022-01680-5"},
                           {"idtype": "pmc", "value": "PMC9388405"}],
            "pubtype": ["Journal Article"],
        }
        line = _fmt_pubmed(d)
        assert line.startswith("PMID 35511416 | 2022 | Smyth B et al. |")
        assert "Sports Med 52(9):2283-2295" in line
        assert "doi:10.1007/s40279-022-01680-5" in line
        assert "PMC9388405" in line
