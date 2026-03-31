import pandas as pd

data = pd.read_json("cdiscount_data.json")
print(len(data))