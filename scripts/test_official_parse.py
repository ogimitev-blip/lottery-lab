import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sync_toto import parse_result

tests=[
    ("https://info.toto.bg/results/6x42/2026-74",74,42,[4,12,14,16,20,42]),
    ("https://info.toto.bg/results/6x49/2026-74",74,49,[1,26,27,34,45,48]),
]
for url,n,maxn,expected in tests:
    r=parse_result(url,n,maxn)
    assert r is not None,url
    assert r["numbers"]==expected,(url,r)
    assert r["date"]=="2026-09-20",(url,r)
    assert r["tiers"][3][1] is not None,(url,r)
print("OFFICIAL_PARSE_OK")
