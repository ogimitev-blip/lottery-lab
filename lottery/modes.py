from .models import current_pool_642,current_pool_649
from .data import load_custom_wheel,load_system36,load_system104,load_system118,load_curated_exact_system
from .wheels import map_positions,build_broad_four,build_broad_six,extend_sequence,cost
from .exact_systems import generate_exact_system

MODE_REGISTRY=[
{"id":"642_6","game":"6/42","name":"6 tickets — K28","status":"Production","k":28,"lines":6,"kind":"custom"},
{"id":"642_18","game":"6/42","name":"K28 custom — 18 lines","status":"Production","k":28,"lines":18,"kind":"custom"},
{"id":"642_30","game":"6/42","name":"K28 custom — 30 lines","status":"Production","k":28,"lines":30,"kind":"custom"},
{"id":"642_50","game":"6/42","name":"K28 custom — 50 lines","status":"Production · main","k":28,"lines":50,"kind":"custom"},
{"id":"642_80","game":"6/42","name":"K28 custom — 80 lines","status":"Analytical / high spend","k":28,"lines":80,"kind":"custom"},
{"id":"642_130","game":"6/42","name":"K28 custom — 130 lines","status":"Analytical / high spend","k":28,"lines":130,"kind":"custom"},
{"id":"642_sys36","game":"6/42","name":"Official System 36 — K28 / 50 lines","status":"Benchmark","k":28,"lines":50,"kind":"benchmark"},
{"id":"642_sys46","game":"6/42","name":"Official System 46 — 20 numbers / 10 lines","status":"Official · budget exact","k":20,"lines":10,"kind":"exact_curated","system_no":46,"guarantee":"3/6"},
{"id":"642_sys28","game":"6/42","name":"Official System 28 — 20 numbers / 18 lines","status":"Official · budget exact","k":20,"lines":18,"kind":"exact_curated","system_no":28,"guarantee":"3/5"},
{"id":"642_sys30","game":"6/42","name":"Official System 30 — 22 numbers / 22 lines","status":"Official · budget exact","k":22,"lines":22,"kind":"exact_curated","system_no":30,"guarantee":"3/5"},
{"id":"642_sys107","game":"6/42","name":"Official System 107 — 10 numbers / 30 lines","status":"Official · budget exact","k":10,"lines":30,"kind":"exact_curated","system_no":107,"guarantee":"3/3 · 4/4 · 5/6"},
{"id":"642_sys105","game":"6/42","name":"Official System 105 — 20 numbers / 39 lines","status":"Official · budget exact","k":20,"lines":39,"kind":"exact_curated","system_no":105,"guarantee":"3/4"},
{"id":"642_sys10","game":"6/42","name":"Official System 10 — 22 numbers / 77 lines","status":"Official · mid-cost exact","k":22,"lines":77,"kind":"exact_curated","system_no":10,"guarantee":"3/3"},
{"id":"642_sys76","game":"6/42","name":"Official System 76 — 20 numbers / 100 lines","status":"Official · mid-cost exact","k":20,"lines":100,"kind":"exact_curated","system_no":76,"guarantee":"3/5 · 4/6"},
{"id":"642_sys104","game":"6/42","name":"Official System 104 — 26 numbers / 130 lines","status":"V10 exact-system challenger","k":26,"lines":130,"kind":"exact","system_no":104,"guarantee":"3/3"},

{"id":"649_k22_4","game":"6/49","name":"4 tickets — K22 broad coverage","status":"Production · low spend","k":22,"lines":4,"kind":"custom"},
{"id":"649_k22_6","game":"6/49","name":"6 tickets — K22","status":"Production","k":22,"lines":6,"kind":"custom"},
{"id":"649_k22_11","game":"6/49","name":"K22 system — 11 lines","status":"Production","k":22,"lines":11,"kind":"custom"},
{"id":"649_k22_16","game":"6/49","name":"K22 system — 16 lines","status":"Production","k":22,"lines":16,"kind":"custom"},
{"id":"649_k22_22","game":"6/49","name":"K22 system — 22 lines","status":"Production","k":22,"lines":22,"kind":"custom"},
{"id":"649_k22_28","game":"6/49","name":"K22 system — 28 lines","status":"Production","k":22,"lines":28,"kind":"custom"},
{"id":"649_k22_33","game":"6/49","name":"K22 system — 33 lines","status":"Production","k":22,"lines":33,"kind":"custom"},
{"id":"649_k26_6","game":"6/49","name":"K26 shadow — 6 lines","status":"Shadow","k":26,"lines":6,"kind":"custom"},
{"id":"649_k26_11","game":"6/49","name":"K26 shadow — 11 lines","status":"Shadow","k":26,"lines":11,"kind":"custom"},
{"id":"649_k26_16","game":"6/49","name":"K26 shadow — 16 lines","status":"Shadow","k":26,"lines":16,"kind":"custom"},
{"id":"649_k26_22","game":"6/49","name":"K26 shadow — 22 lines","status":"Shadow","k":26,"lines":22,"kind":"custom"},
{"id":"649_k26_28","game":"6/49","name":"K26 shadow — 28 lines","status":"Shadow","k":26,"lines":28,"kind":"custom"},
{"id":"649_k26_33","game":"6/49","name":"K26 shadow — 33 lines","status":"Shadow","k":26,"lines":33,"kind":"custom"},
{"id":"649_sys46","game":"6/49","name":"Official System 46 — 20 numbers / 10 lines","status":"Official · budget exact","k":20,"lines":10,"kind":"exact_curated","system_no":46,"guarantee":"3/6"},
{"id":"649_sys28","game":"6/49","name":"Official System 28 — 20 numbers / 18 lines","status":"Official · budget exact","k":20,"lines":18,"kind":"exact_curated","system_no":28,"guarantee":"3/5"},
{"id":"649_sys30","game":"6/49","name":"Official System 30 — 22 numbers / 22 lines","status":"Official · budget exact","k":22,"lines":22,"kind":"exact_curated","system_no":30,"guarantee":"3/5"},
{"id":"649_sys107","game":"6/49","name":"Official System 107 — 10 numbers / 30 lines","status":"Official · budget exact","k":10,"lines":30,"kind":"exact_curated","system_no":107,"guarantee":"3/3 · 4/4 · 5/6"},
{"id":"649_sys105","game":"6/49","name":"Official System 105 — 20 numbers / 39 lines","status":"Official · budget exact","k":20,"lines":39,"kind":"exact_curated","system_no":105,"guarantee":"3/4"},
{"id":"649_sys10","game":"6/49","name":"Official System 10 — 22 numbers / 77 lines","status":"Official · mid-cost exact","k":22,"lines":77,"kind":"exact_curated","system_no":10,"guarantee":"3/3"},
{"id":"649_sys76","game":"6/49","name":"Official System 76 — 20 numbers / 100 lines","status":"Official · mid-cost exact","k":20,"lines":100,"kind":"exact_curated","system_no":76,"guarantee":"3/5 · 4/6"},
{"id":"649_sys118","game":"6/49","name":"Official System 118 — 30 numbers / 131 lines","status":"V10 exact-system challenger","k":30,"lines":131,"kind":"exact","system_no":118,"guarantee":"3/5"},
]

def modes_for_game(game):return [m for m in MODE_REGISTRY if m["game"]==game]
def mode_by_id(mid):return next(m for m in MODE_REGISTRY if m["id"]==mid)

def generate_mode(game,mode_id,draws,target_draw_no=None):
    m=mode_by_id(mode_id)

    if m["kind"] in ("exact","exact_curated"):
        if m["kind"]=="exact_curated":
            spec=load_curated_exact_system(m["system_no"])
            layout=spec["layout"]
        else:
            layout=load_system104() if m["system_no"]==104 else load_system118()
        state=generate_exact_system(game,draws,layout,m["k"])
        state.update({
            "k":m["k"],
            "cost":cost(game,len(state["tickets"]),target_draw_no),
            "label":m["name"],
            "status":m["status"],
            "mode":m,
            "architecture_note":"Exact published reduced system; model ranks are mapped to system positions by exposure, matching the v10 primary backtest mapping. The repeat/flex rule is not used in this exact-system mode.",
            "conversion_version":f"Official System {m['system_no']} · exposure-aware v10",
        })
        return state

    if game=="6/42":
        pool,adds,diag=current_pool_642(draws,28)
        if mode_id=="642_sys36":tickets=map_positions(pool,load_system36())
        else:tickets=map_positions(pool,load_custom_wheel()[:m["lines"]])
        return {"pool":pool,"additions":adds,"diagnostics":diag,"tickets":tickets,"k":28,"cost":cost(game,len(tickets),target_draw_no),"label":m["name"],"status":m["status"],"mode":m}

    k=m["k"];n=m["lines"];pool,adds,diag,score=current_pool_649(draws,k)
    if n==4:
        tickets=build_broad_four(pool,score)
    else:
        base=build_broad_six(pool,score,649)
        tickets=base if n==6 else extend_sequence(base,pool,score,n,20260917+490000)
    return {"pool":pool,"additions":adds,"diagnostics":diag,"tickets":tickets,"k":k,"cost":cost(game,len(tickets),target_draw_no),"label":m["name"],"status":m["status"],"mode":m}
