# Smart Oven Planner (Transportation Reformulation) — Simple README

This project solves many small planning puzzles that look like running a **bakery** with a single oven.

Think of it like this:
- Each day, the oven can work only for a limited time (**capacity**).
- Customers ask for some number of cookies each day (**demand**).
- If you bake a product on a day, you must **turn the oven on** for that product (this costs time and money — **setup**).
- If you bake early and keep items in storage, you pay a small cost for each day they wait (**holding**).

**Goal:** Find a plan that bakes the right amounts on the right days so that
1) all customer demands are met on time,
2) daily capacity is not exceeded, and
3) the **total cost = holding cost + setup cost** is as small as possible.

The code builds a math model and asks **Gurobi** (an optimizer) to find the best plan for **every `.txt` file** in a folder. It writes results to an Excel file.

---

## How it works (in plain words)

- **Inputs (from `.txt` files):** how many products and days, daily capacity, per‑product times/costs, and the demand numbers for each product on each day.
- **Decisions:** For each product and day, do we turn the oven on? How many units do we bake on each earlier day for each later day’s demand?
- **Rules (constraints):**
  - Each day’s demand must be fully satisfied (exactly enough units arrive on that day).
  - Daily capacity cannot be exceeded (time for baking + time for setups ≤ capacity).
  - You cannot bake a product on a day unless you “opened” (setup) that product that day.
- **Objective:** Minimize holding + setup costs.
- **Solver:** Gurobi finds the best plan, or a good plan within a time limit.
- **Output:** One Excel file with a row of results per input file (instance).

### Two special variables (very simplified)
- `y[j,t]` ∈ {0,1}: Did we **turn the oven on** for product `j` on day `t`?
- `x[j,t,r]` ≥ 0: Units of product `j` **baked on day `t`** and **used to satisfy** day `r`’s demand (with `t ≤ r`). If `r > t`, these units wait in storage for `r - t` days and create holding cost.

---

## Input file format (simple)

Each `.txt` file contains:
1. First line: two integers → **number of products** and **number of days**.  
   Example: `5 12`
2. Third line: one number → **daily capacity**.  
   Example: `480`
3. Next `#products` lines: **four numbers per product** →  
   `p  h  sT  sC`  
   where  
   - `p`: processing time per unit (minutes per unit, for capacity)  
   - `h`: holding cost per unit per day  
   - `sT`: setup time (minutes per day when product is baked)  
   - `sC`: setup cost (money per day when product is baked)
4. Remaining lines: **demand numbers** for all products and days (total count = products × days).  
   The reader accepts spaces, commas, or semicolons as separators.

> Tip: Make sure each file is well‑formed; otherwise the parser will raise an error.

---

## Folder layout

Put **all your `.txt` files in one folder** (e.g., `DATA_DIR/`). You can either:
- Run the Python script **from inside that folder** (so `DATA_DIR = Path('.')` works), **or**
- Edit the code to point `DATA_DIR` to the absolute path of your folder, e.g.  
  `DATA_DIR = Path(r"C:\Users\YourName\Desktop\DATA_DIR")`

---

## Requirements

- **Python 3.9+**
- **Gurobi** (installed and licensed) and the Python package `gurobipy`
- Python packages: `pandas` and `openpyxl`

Install Python packages (after Gurobi is installed and licensed):
```bash
pip install gurobipy pandas openpyxl
```

---

## How to run

1) Place the script `Transportation Reformulation2.py` and your `.txt` files as described above.  
2) (Optional) Open the script and adjust the configuration at the top:
   - `DATA_DIR`: where the `.txt` files are
   - `TIME_LIMIT`: per‑file time limit in seconds (e.g., 900)
   - `LIMIT_FILES`: set to a number for testing (e.g., 20), or `None` for all files
   - `SUPPRESS_LOGS`: `True` to hide, `False` to see the Gurobi log
   - `RESULT_XLSX`: output Excel file name

3) Run from a terminal:
```bash
python Transportation Reformulation2.py
```

4) When it finishes, open the Excel file (by default `transportation_results.xlsx`) to see one row per instance and an averages sheet.

**Parallel chunks (optional):**  
You can split work by environment variables, e.g. 4 parts:
```bash
# Linux / macOS
PARTS=4 PART=0 python Transportation Reformulation2.py
PARTS=4 PART=1 python Transportation Reformulation2.py
PARTS=4 PART=2 python Transportation Reformulation2.py
PARTS=4 PART=3 python Transportation Reformulation2.py

# Windows PowerShell
$env:PARTS=4; $env:PART=0; python Transportation Reformulation2.py
```

---

## Example (tiny story)

2 days, 1 product, daily capacity is enough.

- Day 2 needs 10 units.  
- If you bake all 10 on **Day 1**, they wait 1 day → holding cost = `10 × h`. Also you pay setup on Day 1.  
- If you bake all 10 on **Day 2**, no holding cost, but you pay setup on Day 2.  
The solver compares all possibilities (and capacity) and picks the cheapest combination.

---

## Output columns (what they mean)

- `file`: which input file was solved
- `demand_total`: total demand over all products and days
- `inventory_units`: total units that spent time in storage (sum of waiting amounts)
- `holding_cost`: total holding cost
- `setup_cost`: total setup cost
- `total_cost`: holding + setup
- `time_sec`: solve time in seconds
- `gap`: MIP gap reported by Gurobi (0.0 means proven optimal)

The script also builds an **averages sheet**. If your file names don’t match the built‑in regex (e.g., it expects something like `...X123...`), you can either change the regex in the code or replace the grouping with a simple “ALL” average.

---

## Troubleshooting

- **KeyError: 'file' in groupby**  
  Usually means **no `.txt` files were selected** (empty DataFrame).  
  - Check `DATA_DIR` points to the correct folder.
  - Check `PARTS/PART` (with `PARTS=1` and `PART=0` you select all files).
  - Set `LIMIT_FILES=None` to avoid cutting the list to zero.

- **“No `.txt` instances found”**  
  The folder path is wrong or the files use a different extension.

- **Runs forever**  
  Lower `TIME_LIMIT`, or try `SUPPRESS_LOGS=False` to see progress in the Gurobi log.

- **Input parsing errors**  
  Make sure the file structure matches the format above, and that numbers are present for all products × days.

---

## Notes

- This project uses the **transportation reformulation** of the capacitated lot‑sizing model. It creates variables that directly link a production day to the demand day it serves (that’s the `x[j,t,r]` idea). This makes holding costs easy to account for (by multiplying by `(r − t)`).
- Setup has **time** (counts against daily capacity) and **money** (cost in the objective).

---

*Happy planning!* 🧁
