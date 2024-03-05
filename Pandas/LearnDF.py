import pandas as pd
import numpy as np

# Create a DataFrame
df = pd.DataFrame({
    "Name": ["Braund, Mr. Owen Harris",
                "Allen, Mr. William Henry",
                "Bonnell, Miss. Elizabeth"],
    "Age": [22, 35, 58]})

# Print the DataFrame
print(df)
print(df["Name"])
print(df.at[2, "Name"])
print(df == 22)
print(df[df["Age"] > 30])

df = pd.DataFrame([[1, 2, 3],
                   [4, 5, 6],
                   [7, 8, 9],
                   [np.nan, np.nan, np.nan]],
                  columns=['A', 'B', 'C'])

print(df.agg(['sum', 'min']))
print(df.agg({'A' : ['sum', 'min'], 'B' : ['min', 'max']}))
print(df.agg(x=('A', 'max'), y=('B', 'min'), z=('C', 'mean')))
print(df.agg("mean", axis="columns"))
