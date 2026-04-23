import json
notebook_path = r"d:/EMSI/S8/PFA/PFA/src/models/machine_learning_model_advanced_regression.ipynb"
with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

has_errors = False
for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                has_errors = True
                exec_count = cell.get("execution_count", "none")
                ename = output.get("ename", "no_ename")
                evalue = output.get("evalue", "no_evalue")
                print(f"Error in Cell {i} (execution_count={exec_count})")
                print(f"{ename}: {evalue}")
                for line in output.get("traceback", [])[-3:]:
                    print(line)

if not has_errors:
    print("No errors found.")
