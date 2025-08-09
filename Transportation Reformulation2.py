# transportation_reformulation_solver.py – PDF model (first‑2 debug, 40 s)
"""
Solve single‑machine capacitated lot‑sizing instances via the transportation
reformulation (x_{jtr}, y_{jt}) exactly as in Transportation Reformulation Deneme.pdf.

✓ Processes **first 2 files** only (quick validation).  Set `LIMIT_FILES=None`
  for all files.
✓ `TIME_LIMIT = 40` s per instance.
✓ Unit production cost disabled (`UNIT_PROD_COST = 0`).
✓ Writes per‑instance KPIs (demand, inventory, holding, setup) and an
  *averages* sheet.
"""
from __future__ import annotations
import re, time, os
from pathlib import Path
from typing import List, Dict, Any, Sequence

import pandas as pd
import gurobipy as gp
from gurobipy import GRB

# ───────── settings ─────────
DATA_DIR   = Path('.')
TIME_LIMIT = 900               # seconds per instance
UNIT_PROD_COST = 0.0          # production cost ignored
RESULT_XLSX = 'transportation_results.xlsx'
SUPPRESS_LOGS = True
LIMIT_FILES = 540               # None → all files
PARTS = int(os.getenv('PARTS', '1'))
PART  = int(os.getenv('PART',  '0'))
# ----------------------------

_num_re = re.compile(r"[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?")

def _nums(s: str) -> List[float]:
    return [float(m) for m in _nums_re.findall(s)] if (_nums_re := _num_re).search(s) else []

# ───────── robust parser ─────────

def read_instance(path: Path):
    raw = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    nums = _nums(raw[0]) or list(map(float, raw[0].split()))
    if len(nums) < 2:
        raise ValueError('cannot read n_prod n_per')
    n_prod, n_per = map(int, nums[:2])

    cap_nums = _nums(raw[2]) or list(map(float, raw[2].split()))
    if not cap_nums:
        raise ValueError('cannot read capacity line')
    cap = cap_nums[0]

    p, h, sT, sC = [], [], [], []
    for ln in raw[3:3+n_prod]:
        nums = _nums(ln) or [float(tok) for tok in re.split(r'[;,\s]+', ln) if tok.replace('.','',1).isdigit()]
        if len(nums) < 4:
            raise ValueError(f'product line in {path.name} lacks 4 numbers')
        a,b,c,d = nums[:4]
        p.append(a); h.append(b); sT.append(c); sC.append(d)

    # read demand
    vals: List[float] = []
    for ln in raw[3+n_prod:]:
        tok = _nums(ln)
        if not tok:
            for w in re.split(r'[;,\s]+', ln):
                try:
                    tok.append(float(w))
                except ValueError:
                    pass
        vals.extend(tok)
        if len(vals) >= n_prod*n_per:
            break
    if len(vals) < n_prod*n_per:
        raise ValueError('demand truncated')

    d = [[0.0]*n_per for _ in range(n_prod)]
    idx = base = 0
    while base < n_prod:
        blk = min(15, n_prod-base)
        for t in range(n_per):
            for j in range(blk):
                d[base+j][t] = vals[idx]; idx += 1
        base += blk
    return n_prod, n_per, cap, p, h, sT, sC, d

# ───────── model builder (PDF) ─────────

def build_model(tag: str, n: int, T: int, cap: float, p, h, sT, sC, d):
    m = gp.Model(tag)
    if SUPPRESS_LOGS:
        m.Params.OutputFlag = 0
    if TIME_LIMIT:
        m.Params.TimeLimit = TIME_LIMIT

    J = range(n); P = range(T)
    x = m.addVars(((j,t,r) for j in J for t in P for r in range(t,T)), name='x')
    y = m.addVars(((j,t)   for j in J for t in P), vtype=GRB.BINARY, name='y')

    M = [[min(sum(d[j][r] for r in range(t,T)), cap/p[j]) for t in P] for j in J]

    for j in J:
        for r in P:
            m.addConstr(gp.quicksum(x[j,t,r] for t in range(r+1)) == d[j][r])

    for t in P:
        m.addConstr(gp.quicksum(p[j]*gp.quicksum(x[j,t,r] for r in range(t,T)) + sT[j]*y[j,t]
                                for j in J) <= cap)

    for j in J:
        for t in P:
            m.addConstr(gp.quicksum(x[j,t,r] for r in range(t,T)) <= M[j][t]*y[j,t])

    obj = gp.quicksum((r-t)*h[j]*x[j,t,r] for j in J for t in P for r in range(t,T)) + \
          gp.quicksum(sC[j]*y[j,t] for j in J for t in P)
    m.setObjective(obj)
    return m, x, y

STATUS_MAP = {2:'OPTIMAL', 9:'FEASIBLE'}

# ───────── runner ─────────

def main():
    all_files = sorted(DATA_DIR.glob('*.txt'))
    sel = [p for i,p in enumerate(all_files) if i % PARTS == PART]
    if LIMIT_FILES: sel = sel[:LIMIT_FILES]
    print(f"→ solving {len(sel)} of {len(all_files)} instance(s)  LIMIT={TIME_LIMIT}s")

    rows: List[Dict[str,Any]] = []
    for idx, path in enumerate(sel,1):
        n,T,cap,p,h,sT,sC,d = read_instance(path)
        m,x,y = build_model(path.stem,n,T,cap,p,h,sT,sC,d)
        tic = time.perf_counter(); m.optimize(); toc = time.perf_counter()

        inv_units = sum(x[j,t,r].X for j in range(n) for t in range(T) for r in range(t+1,T)) if m.SolCount else None
        hold_cost = sum((r-t)*h[j]*x[j,t,r].X for j in range(n) for t in range(T) for r in range(t+1,T)) if m.SolCount else None
        setup_cnt  = sum(y[j,t].X for j in range(n) for t in range(T)) if m.SolCount else None
        setup_cost = sum(sC[j]*y[j,t].X for j in range(n) for t in range(T)) if m.SolCount else None
        total_cost = hold_cost + setup_cost if m.SolCount else None

        rows.append({
            'file': path.name,
            'status_str': STATUS_MAP.get(m.Status, str(m.Status)),
            'time_sec': round(toc-tic,2),
            'gap': m.MIPGap if m.SolCount else None,
            'demand_total': sum(map(sum,d)),
            'inventory_units': inv_units,
            'holding_cost': hold_cost,
            'setup_cost': setup_cost,
            'setup_count': setup_cnt,
            'total_cost': total_cost,
        })
        print(f"[{idx}/{len(sel)}] {path.name}  {rows[-1]['status_str']}  ({rows[-1]['time_sec']}s)")

    df = pd.DataFrame(rows)
    avg_cols = ['demand_total','inventory_units','holding_cost','setup_cost','total_cost','time_sec','gap']
    avg = (
    df.groupby(df['file'].str.extract(r'X(\d{3})')[0])[avg_cols]
      .mean(numeric_only=True)
      .round(2)
                )


    with pd.ExcelWriter(RESULT_XLSX, engine='openpyxl', mode='w') as xl:
        df.to_excel(xl, sheet_name='instances', index=False)
        avg.to_excel(xl, sheet_name='averages')
    print('Results →', RESULT_XLSX)

if __name__ == '__main__':
    main()
