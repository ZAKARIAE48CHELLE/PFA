import pandas as pd

data = pd.read_json("amazon_deals_data.json")
print(len(data))