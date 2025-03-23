from pandas import read_csv, read_excel


def get_dri_values():
    df = read_excel('/Users/nuthan/Documents/Other Docs/Fitnesss.xlsx', sheet_name='Diet Plan')
    df.drop(columns=['Remarks', 'Unnamed: 32'], inplace=True, axis=1)
    # print(df["Daily Values"])
    # df.T.head()

    df2 = df[['Nutrient', 'Daily Values', 'Unit of Measure']]
    df2['Daily Values'] = df2['Daily Values'].astype(str) + ' ' + df2['Unit of Measure'].astype(str).apply(
        lambda x: x.split("(")[0])
    df2.drop(columns=['Unit of Measure'], inplace=True, axis=1)
    print(df2.head())
    return df2
