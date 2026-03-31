import pandas as pd

data = pd.read_json("./cleaned/cDiscount_data.json")
print(len(data))