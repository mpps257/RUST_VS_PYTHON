import pandas as pd

# ------------------------
# Step 1: Load CSV
# ------------------------
@profile
def load_csv(path):
    return pd.read_csv(path)

# ------------------------
# Step 2: Get column types
# ------------------------
@profile
def get_column_types(df):
    num_cols = df.select_dtypes(include='number').columns.tolist()
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    return num_cols, cat_cols

# ------------------------
# Step 3: Column with most missing
# ------------------------
@profile
def column_most_missing(df, columns):
    # Compute missing count for specified columns
    missing_count = df[columns].isna().sum()

    # Filter out columns that are completely null
    valid_missing = missing_count[missing_count < len(df)]

    # If no valid columns remain or all missing counts are zero, return None
    if valid_missing.empty or valid_missing.max() == 0:
        print("✅ No missing values found in the specified columns.")
        return None

    # print("📊 Missing Values Summary (excluding fully-null columns):")
    # print("-" * 70)
    # print(f"{'Column Name':30} {'Data Type':15} {'Missing Count':15} {'% Missing':>10}")
    # print("-" * 70)

    # # Loop through all valid columns and print stats
    # for col in valid_missing.index:
    #     dtype = df[col].dtype
    #     miss_count = valid_missing[col]
    #     miss_pct = (miss_count / len(df)) * 100
    #     print(f"{col:30} {str(dtype):15} {miss_count:<15} {miss_pct:>9.2f}%")

    # print("-" * 70)

    # Find column with most missing values (but not all null)
    col_with_most_missing = valid_missing.idxmax()
    print(f"🟩 Column with the most missing values: {col_with_most_missing}\n")

    return col_with_most_missing


# ------------------------
# Step 4: Impute numerical column
# ------------------------
@profile
def impute_numerical(df, column, strategy="mean"):
    new_col = f"{column}_imputed_{strategy}"
    df[new_col] = df[column]
    if strategy == "mean":
        df[new_col] = df[new_col].fillna(df[new_col].mean())
    elif strategy == "median":
        df[new_col] = df[new_col].fillna(df[new_col].median())
    return df, new_col

# ------------------------
# Step 5: Process categorical column
# ------------------------
@profile
def process_categorical(df, column, fill_strategy="mode", encode=True, to_upper=True): 
    new_col = f"{column}_processed"
    df[new_col] = df[column]
    if fill_strategy == "mode":
        df[new_col] = df[new_col].fillna(df[new_col].mode()[0]) 
    if to_upper: 
        df[new_col] = df[new_col].str.upper() 
    if encode: 
        df[new_col] = df[new_col].astype("category").cat.codes 
    return df, new_col

# ------------------------
# Step 6: Select or drop columns
# ------------------------
@profile
def select_drop_columns(df, select=None, drop=None):
    if select:
        df = df[select]
    if drop:
        df = df.drop(columns=drop)
    return df

# ------------------------
# Step 7: Filter rows based on a condition
# ------------------------
@profile
def filter_rows(df, condition):
    return df[condition(df)]

# ------------------------
# Step 8: Convert type of a column
# ------------------------
@profile
def convert_type(df, column, dtype):
    new_col = f"{column}_as_{dtype}"
    df[new_col] = df[column].astype(dtype)
    return df, new_col

# ------------------------
# Step 9: Rename columns
# ------------------------
@profile
def rename_columns(df, mapping):
    return df.rename(columns=mapping)

# ------------------------
# Step 10: Sort dataframe
# ------------------------
@profile
def sort_df(df, column, descending=False):
    return df.sort_values(column, ascending=not descending)

# ------------------------
# Step 11: Add derived column
# ------------------------
@profile
def add_column(df, new_col, expr):
    df[new_col] = expr(df)
    return df

# ------------------------
# Step 12: Sample dataframe
# ------------------------
@profile
def sample_df(df, frac=None, n=None):
    if frac is not None:
        return df.sample(frac=frac)
    if n is not None:
        return df.sample(n=n)
    return df

# ------------------------
# Step 13: Aggregate dataframe
# ------------------------
@profile
def aggregate_df(df, group_col, aggs):
    return df.groupby(group_col).agg(aggs).reset_index()

# ------------------------
# Step 14: Normalize numerical column
# ------------------------
@profile
def normalize_column(df, column, method="minmax"):
    new_col = f"{column}_normalized_{method}"
    if method == "minmax":
        min_val = df[column].min()
        max_val = df[column].max()
        df[new_col] = (df[column] - min_val) / (max_val - min_val)
    elif method == "zscore":
        mean = df[column].mean()
        std = df[column].std()
        df[new_col] = (df[column] - mean) / std
    return df, new_col

# ------------------------
# Full pipeline
# ------------------------
@profile
def full_preprocessing_pipeline(path):
    print("\n=== Starting full preprocessing pipeline ===")
    df = load_csv(path)
    print(df.head())
    print(f"Size of Data : {df.shape}")

    # Detect column types
    num_cols, cat_cols = get_column_types(df)
    print(f"Numerical Columns : {num_cols}")
    print(f"Categorical Columns : {cat_cols}")

    #Detect most no of missing values
    num_col = column_most_missing(df, num_cols)
    cat_col = column_most_missing(df, cat_cols)

    print(f"\nMost missing numerical column: {num_col}")
    print(f"Most missing categorical column: {cat_col}")

    # Impute and process
    df, num_imputed = impute_numerical(df, num_col, strategy="mean")
    #df, cat_processed = process_categorical(df, cat_col)

    # Normalize numerical column
    norm_col = "MEDREIMB_CAR"
    df, num_norm = normalize_column(df, norm_col)

    # Convert numerical to integer (new column)
    #df, num_as_int = convert_type(df, num_imputed, "int64")

    # Add derived column (e.g., square of normalized)
    df = add_column(df, f"{num_norm}_squared", lambda d: d[num_norm] ** 2)

    # Filter rows (keep positive normalized)
    df = filter_rows(df, lambda d: d[norm_col] > 10)

    # Sort by normalized column
    df = sort_df(df, num_norm)
    df = sort_df(df, num_norm,True)

    # Rename column (example)
    df = rename_columns(df, {num_norm: f"{num_norm}_renamed"})

    # Aggregate by numerical column (mean of numeric)
    #df_agg = aggregate_df(df, num_imputed, {f"{num_norm}_renamed": "mean"})

    # Select subset and drop
    drop_col = "SP_STRKETIA"
    select_col = "BENE_COUNTY_CD"
    df_drop = select_drop_columns(df, select=None, drop=[drop_col])
    df_select = select_drop_columns(df, select=[select_col], drop=None)

    # Sample a fraction (10%)
    df_sampled = sample_df(df_select, frac=0.1)

    print("\n=== Pipeline Complete ===")
    return {
        "original": df,
        "sampled": df_sampled,
        "num_col": num_col,
        "cat_col": cat_col
    }

# ------------------------
# Main execution
# ------------------------
@profile
def main():
    path = r"C:\Users\pm018586\OneDrive - Zelis Healthcare\Documents\Presentations\Data Preprocessing Python VS Rust\Datasets\176541_DE1_0_2008_Beneficiary_Summary_File_Sample_1\DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv"
    
    results = full_preprocessing_pipeline(path)
    print(f"\nNumerical column processed: {results['num_col']}")
    print(f"Categorical column processed: {results['cat_col']}")
    print("\nSample of processed data:")
    print(results['sampled'].head())

if __name__ == "__main__":
    main()