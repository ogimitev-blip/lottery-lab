import itertools,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
lib=json.loads((ROOT/"systems"/"official_exact_curated.json").read_text())

for sid,spec in lib.items():
    k=int(spec["k"])
    rows=[tuple(map(int,r)) for r in spec["layout"]]
    assert len(rows)==len(set(rows)),f"System {sid}: duplicate rows"
    assert all(len(r)==6 and len(set(r))==6 and min(r)>=1 and max(r)<=k for r in rows),f"System {sid}: invalid row"
    sets=[set(r) for r in rows]
    for target,known in spec["guarantees"]:
        min_best=6
        for winners in itertools.combinations(range(1,k+1),int(known)):
            ws=set(winners)
            best=max(len(ws&t) for t in sets)
            min_best=min(min_best,best)
            if min_best<int(target):
                break
        assert min_best>=int(target),f"System {sid} fails published {target}/{known}; min={min_best}"
    print(f"System {sid}: K{k}, {len(rows)} lines, guarantees OK")

print("CURATED_EXACT_SYSTEMS_OK")
