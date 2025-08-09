# Transportation Reformulation Lot‑Sizing Solver (Gurobi)

This repository contains a Python script that solves a **capacitated lot‑sizing** problem using a **transportation reformulation**. It reads one or more plain‑text instance files, builds a mixed‑integer program (MIP) in Gurobi, and minimizes **inventory holding** + **setup** costs subject to capacity and demand‑fulfillment constraints. Results for all instances are summarized into an Excel workbook.

> Script: `Transportation Reformulation2.py`  
> Example instance: `X11117A.txt`

---

## ✨ What this solver does

- Parses a folder of `.txt` instances (each encoding products, periods, capacity, per‑product parameters, and a demand matrix).
- Builds a **transportation‑style lot‑sizing model** with variables:
  - `x[j,t,r] ≥ 0`: quantity of product *j* produced in period *t* and used to satisfy demand in period *r* (only for `r ≥ t`).
  - `y[j,t] ∈ {0,1}`: setup decision for product *j* in period *t*.
- Enforces for every product and period:
  - Demand satisfaction: 

    \[ \sum_{t=0}^{r} x_{jtr} = d_{jr} \quad \forall j, r \]
  - Capacity per period: 

    \[ \sum_j \Big( p_j \sum_{r\ge t} x_{jtr} + sT_j\, y_{jt} \Big) \le \text{cap} \quad \forall t \]
  - Setup linkage (Big‑M): if there is no setup, there can be no production flow in that period: 

    \[ \sum_{r\ge t} x_{jtr} \le M_{jt} \; y_{jt} \]
- Minimizes total cost (no unit production cost here): 

  \[ \min \sum_{j,t,r} (r-t)\,h_j\,x_{jtr} + \sum_{j,t} sC_j\,y_{jt} \]

Outputs include per‑instance KPIs (inventory units, holding cost, setup cost, setup count, total cost, time, MIP gap) and an **Excel report** with a row per instance and an optional **averages** sheet grouped by filename pattern (e.g., `X123`).

---

## 📦 Requirements

- Python 3.9+
- [Gurobi Optimizer](https://www.gurobi.com/) and a valid license
- `gurobipy`
- `pandas`, `openpyxl`

Install Python packages:
```bash
pip install gurobipy pandas openpyxl
```

> **Note:** You must have a working Gurobi installation and license. See Gurobi’s docs for setup instructions.

---

## 📁 Input format (plain text)

Each instance `.txt` file uses the layout below:

1. **Line 1**: two integers → number of products `n_prod` and number of periods `n_per`  
2. **Line 2**: a single integer (legacy/ignored by the model)  
3. **Line 3**: an integer or float → *per‑period capacity* `cap`  
4. **Next `n_prod` lines**: four numbers per line (for product *j*)  
   - `p_j` → processing time / capacity usage per unit  
   - `h_j` → holding cost per unit per period  
   - `sT_j` → setup time (capacity usage)  
   - `sC_j` → setup cost  
5. **Remaining numbers**: exactly `n_prod * n_per` non‑negative demand values (arbitrary whitespace/line breaks are fine). The parser stops once it reads that many numbers; any trailing text is ignored.

### 🧾 Minimal example (`X11117A.txt` excerpt)

```text
10 20              # n_prod n_per
1                  # (legacy value, ignored)
1332               # capacity per period
# p     h     sT   sC  (10 lines follow)
1.00  0.80  17   37
0.90  0.60  17   37
...
# then demands: n_prod * n_per = 10 * 20 = 200 values, e.g.
0 115 116 0 0 92  ... (continues until 200 numbers read)
...
```

> Demands are mapped into a `n_prod × n_per` matrix. For product *j* and period *r*, `d[j,r]` is the `r`‑th demand of product *j*.

---

## ⚙️ Configuration (edit at the top of the script)

- `DATA_DIR`: directory to scan for `.txt` files (default: current folder)
- `TIME_LIMIT`: solver time limit **per instance** in seconds (default: `900`)
- `UNIT_PROD_COST`: fixed to `0.0` (not used in the objective)
- `RESULT_XLSX`: name of the Excel summary file (default: `transportation_results.xlsx`)
- `LIMIT_FILES`: cap on the number of instances to process (e.g., `540`)
- **Sharding** for batch runs on multiple processes:
  - `PARTS`: total number of shards (e.g., `4`)
  - `PART`: zero‑based shard index to run (e.g., `0`, `1`, `2`, `3`)

---

## ▶️ How to run

1. Place your instance files (e.g., `X*.txt`) in `DATA_DIR` (or run the script from the folder that contains them).
2. Run:
   ```bash
   python Transportation\ Reformulation2.py
   ```
3. After solving, check `transportation_results.xlsx`:
   - **Sheet `instances`**: one row per instance with KPIs and timings.
   - **Sheet `averages`**: optional, averages grouped by the filename pattern `X(\d{3})` (e.g., `X111`, `X117`).

> If your filenames don’t match `X###...`, the `averages` sheet grouping may be empty. That’s expected.

---

## 📊 KPIs & Output fields

- `file`: instance filename
- `n_prod`, `n_per`, `cap`: basic instance data
- `demand_total`: sum of all demands
- `inventory_units`: total units carried across periods (sum of flows with `r>t`)
- `holding_cost`, `setup_cost`, `setup_count`
- `total_cost = holding_cost + setup_cost`
- `time_sec`: solve time for that instance
- `gap`: best MIP gap reported by Gurobi

---

## 🧠 Modeling notes

- **Transportation reformulation** turns lot‑sizing into a flow model across time, which often strengthens relaxations versus naïve inventory‑balance formulations.
- **Big‑M values** `M_{j,t}` are chosen conservatively as the minimum of “future demand sum” and a capacity‑based upper bound to help the solver.
- Unit production cost is intentionally ignored (set to zero) in the objective; only **holding** and **setup** costs drive optimization.

---

## 🚀 Performance tips

- Decrease `TIME_LIMIT` while prototyping; raise it for final runs.
- Keep demand non‑negative and ensure per‑period capacity is realistic relative to `p_j` and `sT_j`.
- If you have thousands of periods/products, consider batching instances and using **sharding** (`PARTS` / `PART`).

---

## 🔧 Troubleshooting

- **Infeasible model**: check period capacity vs. the minimum processing time required by demands; also confirm that setup times do not exhaust capacity.
- **Empty `averages` sheet**: ensure filenames match the regex `X(\d{3})` if you want group averages.
- **Parser errors**: verify that you have exactly `n_prod * n_per` demand values and exactly `n_prod` lines of product parameters.


