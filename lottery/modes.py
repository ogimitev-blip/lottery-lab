from .models import current_pool_642,current_pool_649
from .data import load_custom_wheel,load_system36
from .wheels import map_positions,build_broad_six,extend_sequence,cost

MODES_642=[
    ("642_6","6 tickets — K28",6),
    ("642_18","K28 custom — 18 lines",18),
    ("642_30","K28 custom — 30 lines",30),
    ("642_50","K28 custom — 50 lines",50),
    ("642_80","K28 custom — 80 lines",80),
    ("642_130","K28 custom — 130 lines",130),
    ("642_sys36","Official System 36 — K28 / 50 lines",50),
]
MODES_649=[
    ("649_k22_6","6 tickets — K22 production",6),
    ("649_k22_11","K22 system — 11 lines",11),
    ("649_k22_16","K22 system — 16 lines",16),
    ("649_k22_22","K22 system — 22 lines",22),
    ("649_k22_28","K22 system — 28 lines",28),
    ("649_k22_33","K22 system — 33 lines",33),
    ("649_k26_6","K26 shadow — 6 lines",6),
    ("649_k26_11","K26 shadow — 11 lines",11),
    ("649_k26_16","K26 shadow — 16 lines",16),
    ("649_k26_22","K26 shadow — 22 lines",22),
    ("649_k26_28","K26 shadow — 28 lines",28),
    ("649_k26_33","K26 shadow — 33 lines",33),
]

def modes_for_game(game):
    return MODES_642 if game=="6/42" else MODES_649

def generate_mode(game,mode_id,draws):
    if game=="6/42":
        pool,adds,diag=current_pool_642(draws,28)
        if mode_id=="642_sys36":
            tickets=map_positions(pool,load_system36())
            label="Official System 36"; k=28
        else:
            n=int(mode_id.split("_")[-1]); tickets=map_positions(pool,load_custom_wheel()[:n]); label=f"K28 custom {n}"; k=28
        return {"pool":pool,"additions":adds,"diagnostics":diag,"tickets":tickets,"k":k,"cost":cost(game,len(tickets)),"label":label}
    parts=mode_id.split("_"); k=22 if parts[1]=="k22" else 26; n=int(parts[-1])
    pool,adds,diag,score=current_pool_649(draws,k)
    base=build_broad_six(pool,score,649)
    tickets=base if n==6 else extend_sequence(base,pool,score,n,20260917+490000+k)
    return {"pool":pool,"additions":adds,"diagnostics":diag,"tickets":tickets,"k":k,"cost":cost(game,len(tickets)),"label":f"K{k} {'production' if k==22 else 'shadow'} {n}"}
