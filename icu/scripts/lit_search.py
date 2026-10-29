"""文献检索小工具：PubMed（E-utilities）、Europe PMC REST、Crossref。只用标准库。

供 vault/evidence/ 研究卡片库检索和核对文献用（流程见 vault/evidence/_template.md）。

用法（在 icu/ 目录下）：
  python scripts/lit_search.py pubmed   "<query>" [--n 20] [--from 2023] [--reviews]
  python scripts/lit_search.py epmc     "<query>" [--n 25] [--from 2023] [--abstracts] [--sort relevance|cited|date]
  python scripts/lit_search.py record   <PMID|PMCID|DOI>            # 单条：全部作者、全文链接、完整摘要
  python scripts/lit_search.py cites    <PMID> [--q "<extra terms>"] [--from 2023] [--n 40] [--sort cited|date]
  python scripts/lit_search.py refs     <PMID> [--n 300]
  python scripts/lit_search.py crossref <DOI>                       # 出版社登记的元数据 + 更正/撤稿通知
  python scripts/lit_search.py fulltext <PMCID> --out <file.txt>    # Europe PMC 开放全文 -> 纯文本（含节标题、表格、图注）

每个请求的原始返回按 URL 哈希缓存到 LIT_RAW_DIR（默认 icu_data_warehouse/9_Coach_Raw/lit_search_cache，
git 忽略），同一 URL 不重复请求；_urls.tsv 记录每个缓存文件对应的 URL 和抓取时间。
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

RAW_DIR = Path(os.environ.get(
    "LIT_RAW_DIR",
    Path(__file__).resolve().parents[1] / "icu_data_warehouse" / "9_Coach_Raw" / "lit_search_cache",
))
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
CROSSREF = "https://api.crossref.org/works"
UA = "cycling-evidence-cards/0.1 (literature verification script)"
REVIEW_FILTER = (
    '(review[pt] OR systematic review[pt] OR meta-analysis[pt] '
    'OR "consensus development conference"[pt] OR practice guideline[pt] OR guideline[pt])'
)
EPMC_SORT = {"relevance": None, "cited": "CITED desc", "date": "P_PDATE_D desc"}
# 只匹配真正的标签（<i>、</sup>…）：标签名必须紧跟在 < 或 </ 后面
_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9:-]*(?:\s[^<>]*)?/?>")


# ---------- 网络与缓存 ----------

def _get(url: str, *, ncbi: bool) -> str:
    delay = 1.0
    for attempt in range(6):
        if ncbi:
            time.sleep(0.4)  # NCBI 无 key 限速 3 次/秒
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(delay)
                delay *= 2
                continue
            raise SystemExit(f"ERROR HTTP {e.code} {url}") from e
        except urllib.error.URLError as e:
            if attempt < 5:
                time.sleep(delay)
                delay *= 2
                continue
            raise SystemExit(f"ERROR network {e.reason} {url}") from e
    raise SystemExit(f"ERROR retries exhausted {url}")


def fetch(url: str, *, ncbi: bool = False, text: bool = False):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    suffix = ".xml" if text else ".json"
    name = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16] + suffix
    cache = RAW_DIR / name
    if cache.exists():
        data = cache.read_text(encoding="utf-8")
    else:
        data = _get(url, ncbi=ncbi)
        tmp = cache.with_suffix(cache.suffix + f".{os.getpid()}.tmp")
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, cache)
        with (RAW_DIR / "_urls.tsv").open("a", encoding="utf-8") as f:
            f.write(f"{name}\t{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{url}\n")
    if text:
        return data
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR non-JSON response cached in {cache}") from e


# ---------- 格式化 ----------

def _clean(s: str) -> str:
    """去掉标签、反转义实体、压缩空白；保留正文里的比较符号（p < 0.05、<70 kg）。"""
    return re.sub(r"\s+", " ", _TAG.sub(" ", html.unescape(s or ""))).strip()


def _first_author(author_string: str) -> str:
    parts = [p.strip() for p in (author_string or "").split(",") if p.strip()]
    if not parts:
        return "?"
    return parts[0] + (" et al." if len(parts) > 1 else "")


def _fmt_pubmed(d: dict) -> str:
    ids = {x.get("idtype"): x.get("value") for x in d.get("articleids", [])}
    authors = d.get("authors", [])
    first = authors[0]["name"] if authors else "?"
    etal = " et al." if len(authors) > 1 else ""
    cite = f"{d.get('source', '')} {d.get('volume', '')}({d.get('issue', '')}):{d.get('pages', '')}"
    return (
        f"PMID {d.get('uid')} | {(d.get('pubdate') or '')[:4]} | {first}{etal} | {d.get('title', '')} | "
        f"{cite} | doi:{ids.get('doi', '-')} | {ids.get('pmc', '-')} | {';'.join(d.get('pubtype', []))}"
    )


def _fmt_epmc(r: dict) -> str:
    ji = r.get("journalInfo", {}) or {}
    j = ji.get("journal", {}) or {}
    pts = (r.get("pubTypeList", {}) or {}).get("pubType", [])
    if r.get("isOpenAccess") == "Y":
        oa = "OA"
    elif r.get("inPMC") == "Y" or r.get("pmcid"):
        oa = "inPMC"
    else:
        oa = "-"
    return (
        f"{r.get('source')}:{r.get('id')} | {r.get('pubYear')} | {_first_author(r.get('authorString', ''))} | "
        f"{_clean(r.get('title', ''))} | {j.get('isoabbreviation') or j.get('title', '')} "
        f"{ji.get('volume', '')}({ji.get('issue', '')}):{r.get('pageInfo', '')} | doi:{r.get('doi', '-')} | "
        f"pmid:{r.get('pmid', '-')} | {r.get('pmcid', '-')} | {oa} | cited:{r.get('citedByCount', 0)} | {';'.join(pts)}"
    )


def _date_parts(m: dict, key: str):
    return ((m.get(key) or {}).get("date-parts") or [[None]])[0]


# ---------- 命令 ----------

def cmd_pubmed(a) -> None:
    term = f"({a.query}) AND {REVIEW_FILTER}" if a.reviews else a.query
    params = {"db": "pubmed", "term": term, "retmode": "json", "retmax": a.n,
              "sort": "relevance", "tool": "cycling-evidence"}
    if a.from_year:
        params.update({"datetype": "pdat", "mindate": str(a.from_year), "maxdate": "3000"})
    es = fetch(f"{EUTILS}/esearch.fcgi?{urllib.parse.urlencode(params)}", ncbi=True)
    res = es.get("esearchresult", {})
    ids = res.get("idlist", [])
    print(f"# PubMed hits={res.get('count')} shown={len(ids)} from={a.from_year or 'any'} term={term}")
    if not ids:
        return
    sp = {"db": "pubmed", "id": ",".join(ids), "retmode": "json", "tool": "cycling-evidence"}
    sm = fetch(f"{EUTILS}/esummary.fcgi?{urllib.parse.urlencode(sp)}", ncbi=True)
    for pmid in ids:
        print(_fmt_pubmed(sm.get("result", {}).get(pmid, {"uid": pmid})))


def _epmc_search(query: str, n: int, sort: str | None) -> dict:
    params = {"query": query, "format": "json", "pageSize": n, "resultType": "core"}
    if sort:
        params["sort"] = sort
    return fetch(f"{EPMC}/search?{urllib.parse.urlencode(params)}")


def cmd_epmc(a) -> None:
    q = f"({a.query}) AND PUB_YEAR:[{a.from_year} TO 2030]" if a.from_year else a.query
    d = _epmc_search(q, a.n, EPMC_SORT[a.sort])
    res = (d.get("resultList", {}) or {}).get("result", [])
    print(f"# EuropePMC hits={d.get('hitCount')} shown={len(res)} sort={a.sort} query={q}")
    for r in res:
        print(_fmt_epmc(r))
        if a.abstracts:
            print("   ABSTRACT: " + _clean(r.get("abstractText", "")))


def cmd_record(a) -> None:
    i = a.id.strip()
    if i.upper().startswith("PMC"):
        q = f"PMCID:{i.upper()}"
    elif i.isdigit():
        q = f"EXT_ID:{i} AND SRC:MED"
    else:
        q = f'DOI:"{i}"'
    d = _epmc_search(q, 5, None)
    res = (d.get("resultList", {}) or {}).get("result", [])
    if not res:
        print(f"NOT FOUND in Europe PMC: {q}")
        return
    r = res[0]
    print(_fmt_epmc(r))
    print("AUTHORS: " + (r.get("authorString") or ""))
    urls = (r.get("fullTextUrlList", {}) or {}).get("fullTextUrl", [])
    print("FULLTEXT: " + "; ".join(
        f"{u.get('availability')}:{u.get('documentStyle')}:{u.get('url')}" for u in urls))
    print("KEYWORDS: " + "; ".join(str(k) for k in (r.get("keywordList", {}) or {}).get("keyword", []) if k))
    print("ABSTRACT: " + _clean(r.get("abstractText", "")))


def cmd_cites(a) -> None:
    q = f"CITES:{a.pmid}_MED"
    if a.q:
        q += f" AND ({a.q})"
    if a.from_year:
        q += f" AND PUB_YEAR:[{a.from_year} TO 2030]"
    d = _epmc_search(q, a.n, EPMC_SORT[a.sort])
    res = (d.get("resultList", {}) or {}).get("result", [])
    print(f"# citing PMID {a.pmid}: hits={d.get('hitCount')} shown={len(res)} sort={a.sort} query={q}")
    for r in res:
        print(_fmt_epmc(r))


def cmd_refs(a) -> None:
    d = fetch(f"{EPMC}/MED/{a.pmid}/references?format=json&pageSize=1000")
    lst = (d.get("referenceList", {}) or {}).get("reference", [])
    print(f"# references of PMID {a.pmid}: total={d.get('hitCount')} shown={min(len(lst), a.n)}")
    for r in lst[: a.n]:
        print(f"{r.get('source', '-')}:{r.get('id', '-')} | {r.get('pubYear', '')} | "
              f"{_first_author(r.get('authorString', ''))} | {_clean(r.get('title', ''))} | "
              f"{r.get('journalAbbreviation', '')}")


def cmd_crossref(a) -> None:
    doi = a.doi.strip()
    m = fetch(f"{CROSSREF}/{urllib.parse.quote(doi)}").get("message", {})
    authors = "; ".join(
        f"{x.get('family', '')} {x.get('given', '')}".strip() or x.get("name", "")
        for x in m.get("author", []))
    print(f"TITLE: {_clean(' '.join(m.get('title', [])))}")
    print(f"AUTHORS: {authors}")
    print(f"JOURNAL: {' '.join(m.get('container-title', []))} | vol {m.get('volume', '')} "
          f"issue {m.get('issue', '')} pages {m.get('page', '')} | article-number {m.get('article-number', '')}")
    print(f"DATES: issued {_date_parts(m, 'issued')} | print {_date_parts(m, 'published-print')} | "
          f"online {_date_parts(m, 'published-online')}")
    print(f"TYPE: {m.get('type')} | DOI: {m.get('DOI')} | publisher: {m.get('publisher')} | "
          f"cited-by(crossref): {m.get('is-referenced-by-count')}")
    print(f"UPDATED-BY: {json.dumps(m.get('updated-by', []), ensure_ascii=False)}")
    print(f"UPDATE-TO: {json.dumps(m.get('update-to', []), ensure_ascii=False)}")
    u = fetch(f"{CROSSREF}?{urllib.parse.urlencode({'filter': f'updates:{doi}', 'rows': 20})}")
    items = u.get("message", {}).get("items", [])
    print(f"NOTICES POINTING AT THIS DOI (corrections/retractions): {len(items)}")
    for it in items:
        kinds = ",".join(x.get("type", "") for x in it.get("update-to", []))
        print(f"  - {kinds} | {it.get('DOI')} | {_clean(' '.join(it.get('title', [])))}")


def _text(el) -> str:
    return _clean("".join(el.itertext()))


def _walk(el, out: list[str], depth: int) -> None:
    tag = el.tag.split("}")[-1]
    if tag == "sec":
        title = el.find("title")
        if title is not None:
            out.append("\n" + "#" * min(depth + 2, 6) + " " + _text(title))
        for child in el:
            if child.tag.split("}")[-1] != "title":
                _walk(child, out, depth + 1)
        return
    if tag == "p":
        out.append(_text(el))
        return
    if tag == "table-wrap":
        label = el.find("label")
        cap = el.find("caption")
        out.append(f"\n[TABLE] {_text(label) if label is not None else ''} {_text(cap) if cap is not None else ''}")
        for tr in el.iter():
            if tr.tag.split("}")[-1] == "tr":
                cells = [_text(c) for c in tr if c.tag.split("}")[-1] in ("td", "th")]
                out.append(" | ".join(cells))
        for fn in el.iter():
            if fn.tag.split("}")[-1] == "table-wrap-foot":
                out.append("[TABLE FOOTNOTE] " + _text(fn))
        return
    if tag == "fig":
        label = el.find("label")
        cap = el.find("caption")
        out.append(f"\n[FIGURE] {_text(label) if label is not None else ''} {_text(cap) if cap is not None else ''}")
        return
    if tag in ("ref-list", "ack"):
        return
    for child in el:
        _walk(child, out, depth)


def cmd_fulltext(a) -> None:
    pmcid = a.pmcid.strip().upper()
    xml = fetch(f"{EPMC}/{pmcid}/fullTextXML", text=True)
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise SystemExit(f"ERROR XML parse failed for {pmcid}: {e}") from e
    out: list[str] = [f"# FULL TEXT {pmcid} (Europe PMC fullTextXML)"]
    tg = root.find(".//article-title")
    if tg is not None:
        out.append("TITLE: " + _text(tg))
    ab = root.find(".//abstract")
    if ab is not None:
        out.append("\n## Abstract")
        _walk(ab, out, 0)
    body = root.find(".//body")
    if body is not None:
        _walk(body, out, 0)
    back = root.find(".//back")
    if back is not None:
        for child in back:
            if child.tag.split("}")[-1] not in ("ref-list", "ack"):
                _walk(child, out, 0)
    Path(a.out).write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {a.out} ({sum(len(x) for x in out)} chars)")


def main(argv: list[str] | None = None) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("pubmed")
    s.add_argument("query")
    s.add_argument("--n", type=int, default=20)
    s.add_argument("--from", dest="from_year", type=int)
    s.add_argument("--reviews", action="store_true")
    s.set_defaults(func=cmd_pubmed)

    s = sub.add_parser("epmc")
    s.add_argument("query")
    s.add_argument("--n", type=int, default=25)
    s.add_argument("--from", dest="from_year", type=int)
    s.add_argument("--abstracts", action="store_true")
    s.add_argument("--sort", choices=list(EPMC_SORT), default="relevance")
    s.set_defaults(func=cmd_epmc)

    s = sub.add_parser("record")
    s.add_argument("id")
    s.set_defaults(func=cmd_record)

    s = sub.add_parser("cites")
    s.add_argument("pmid")
    s.add_argument("--q")
    s.add_argument("--from", dest="from_year", type=int)
    s.add_argument("--n", type=int, default=40)
    s.add_argument("--sort", choices=list(EPMC_SORT), default="cited")
    s.set_defaults(func=cmd_cites)

    s = sub.add_parser("refs")
    s.add_argument("pmid")
    s.add_argument("--n", type=int, default=300)
    s.set_defaults(func=cmd_refs)

    s = sub.add_parser("crossref")
    s.add_argument("doi")
    s.set_defaults(func=cmd_crossref)

    s = sub.add_parser("fulltext")
    s.add_argument("pmcid")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_fulltext)

    a = p.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
