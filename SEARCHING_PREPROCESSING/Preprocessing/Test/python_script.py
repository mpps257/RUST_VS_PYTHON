#!/usr/bin/env python3
"""
pandas_clean_and_profile.py

Usage:
    python pandas_clean_and_profile.py --input input.csv --out cleaned_pandas.csv --log pandas_log.txt

What it does:
- Loads CSV with pandas
- Runs a small generic preprocessing pipeline (column name cleanup, trim strings, parse date-ish cols,
  fill missing values, drop duplicates)
- Samples process RSS regularly to estimate peak memory usage
- Logs timings and peak memory to a text log
"""

import argparse
import os
import time
import threading
import psutil                 # pip install psutil
import pandas as pd           # pip install pandas
import numpy as np
from collections import Counter
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler

@profile
def memory_monitor(pid, interval_s, stop_event, samples):
    """
    Runs in a background thread: samples process RSS and appends to samples list until stop_event is set.
    pid: process id (int)
    interval_s: sample interval in seconds (float)
    stop_event: threading.Event
    samples: list to append RSS values (bytes)
    """
    proc = psutil.Process(pid)
    while not stop_event.is_set():
        try:
            rss = proc.memory_info().rss
            samples.append(rss)
        except Exception:
            # could occur if process ended; ignore
            pass
        time.sleep(interval_s)

@profile
def infer_date_like(series, sample=2000, threshold=0.5):
    """
    Heuristic: try to parse a sample of the column as datetime; if at least `threshold` fraction parses,
    treat column as date-like.
    Returns parsed Series (with NaT where not parseable) or None.
    """
    # sample rows (fast)
    s = series.dropna()
    if s.empty:
        return None
    samp = s.head(sample).astype(str)
    parsed = pd.to_datetime(samp, errors="coerce", infer_datetime_format=True)
    frac = parsed.notna().sum() / len(parsed)
    if frac >= threshold:
        # parse full column
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)
    return None

@profile
def log_memory(step_name):
    """Logs the current and peak memory usage at this point."""
    proc = psutil.Process(os.getpid())
    current_rss = proc.memory_info().rss
    return f"[MEMORY] {step_name}: current RSS = {current_rss:,} bytes"


def main():
    print("Code running")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="input CSV path")
    parser.add_argument("--out", default="cleaned_pandas.csv", help="output cleaned CSV path")
    parser.add_argument("--log", default="pandas_log.txt", help="log file path")
    parser.add_argument("--sample-ms", type=int, default=50, help="memory sample interval in ms")
    args = parser.parse_args()

    pid = os.getpid()
    mem_samples = []
    stop_event = threading.Event()
    monitor = threading.Thread(target=memory_monitor, args=(pid, args.sample_ms / 1000.0, stop_event, mem_samples), daemon=True)

    # open log file (text)
    with open(args.log, "w", encoding="utf-8") as log:
        def logw(s=""):
            log.write(s + "\n")
            log.flush()

        logw(f"Pandas preprocessing log")
        logw(f"Input: {args.input}")
        logw(f"Start time: {time.ctime()}")

        overall_start = time.perf_counter()
        monitor.start()  # start memory sampler

        # --- STEP 1: read CSV ---
        step_start = time.perf_counter()
        # low_memory=False gives more consistent dtypes; adjust chunksize if you want streaming
        df = pd.read_csv(args.input, low_memory=False)
        step_elapsed = time.perf_counter()
        - step_start
        logw(f"[STEP read_csv] elapsed_s={step_elapsed:.4f} rows={len(df)} cols={len(df.columns)}")
        logw(f"Memory (pandas DataFrame memory_usage deep) = {df.memory_usage(deep=True).sum():,} bytes \n\n")
        logw(log_memory("[READ CSV]"))

        # --- STEP 2: canonicalize column names (strip + lower) ---
        step_start = time.perf_counter()
        old_cols = list(df.columns)
        new_cols = [str(c).strip().lower() for c in old_cols]
        df.columns = new_cols
        step_elapsed = time.perf_counter() - step_start
        logw(f"[STEP normalize_columns] elapsed_s={step_elapsed:.4f}")
        logw(f"Column sample before->after: {old_cols[:6]} -> {new_cols[:6]}\n\n")
        logw(log_memory("[COLUMN NORM]"))

        # --- STEP 3: trim whitespace in string columns and convert empty strings to NaN ---
        step_start = time.perf_counter()
        obj_cols = df.select_dtypes(include=["object"]).columns.tolist()
        for c in obj_cols:
            # .str.strip preserves NaN values; then replace empty strings with NaN
            df[c] = df[c].astype("string")   # pandas string dtype handles missing properly
            df[c] = df[c].str.strip()
            # convert empty strings to <NA>
            df[c] = df[c].replace("", pd.NA)
        step_elapsed = time.perf_counter() - step_start
        logw(f"[STEP trim_strings] elapsed_s={step_elapsed:.4f} string_cols={len(obj_cols)}\n\n")
        logw(log_memory("[TRIM STR]"))

        # --- STEP 4: detect and parse date-like columns (heuristic: column name contains 'date' OR parseable) ---
        step_start = time.perf_counter()
        parsed_dates = []
        for c in df.columns:
            if "date" in c:
                parsed = infer_date_like(df[c])
                if parsed is not None:
                    df[c] = parsed
                    parsed_dates.append(c)
        # also try to detect other string columns that are strongly date-like
        for c in df.select_dtypes(include=["string", "object"]).columns:
            if c in parsed_dates:
                continue
            parsed = infer_date_like(df[c])
            if parsed is not None:
                df[c] = parsed
                parsed_dates.append(c)
        step_elapsed = time.perf_counter() - step_start
        logw(f"[STEP parse_dates] elapsed_s={step_elapsed:.4f} parsed_date_columns={parsed_dates}")
        logw(log_memory("[PARSE DATELIKE]"))

        # --- STEP 5: fill missing values (numeric -> median, categorical -> mode) ---
        step_start = time.perf_counter()
        logw("\n[STEP fill_missing] --- Starting missing value imputation ---")

        # numeric columns
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        logw(f"Identified {len(num_cols)} numeric columns: {num_cols}")

        for c in num_cols:
            col_start = time.perf_counter()  # ⏱️ start timing for this column

            median = df[c].median(skipna=True)
            logw(f"Time to calculate median : {time.perf_counter() - col_start}")
            if np.isnan(median):
                logw(f"Column '{c}': median could not be computed (all NaN) — skipped.")
                continue

            logw(f"Column '{c}': median = {median:.4f}")
            missing_before = df[c].isna().sum()
            df[c] = df[c].fillna(median)
            missing_after = df[c].isna().sum()

            col_elapsed = time.perf_counter() - col_start  # ⏱️ end timing
            logw(f"Filled {missing_before - missing_after} missing values in '{c}' "
                f"using median {median:.4f} | elapsed = {col_elapsed:.4f}s")
            logw(log_memory(f"[DATA IMPUTATION - {c}]"))
        
        logw(f"[STEP fill_missing in numerical] Completed in {time.perf_counter()-step_start:.4f} seconds "
            f"(numeric_cols={len(num_cols)})")
        logw(log_memory(f"[DATA IMPUTATION NUMERICAL OVERALL]"))

        # categorical/string columns: fill with mode if available
        cat_cols = df.select_dtypes(include=["string", "category", "object"]).columns.tolist()
        logw(f"Identified {len(cat_cols)} categorical columns: {cat_cols}")

        start_cat = time.perf_counter()
        for c in cat_cols:
            col_start = time.perf_counter()  # ⏱️ start timing for this column

            try:
                mode_series = df[c].mode(dropna=True)
                if not mode_series.empty:
                    mode_val = mode_series.iloc[0]
                    logw(f"Time to calculate mode of {c} : {time.perf_counter() - col_start}")
                    missing_before = df[c].isna().sum()
                    df[c] = df[c].fillna(mode_val)
                    missing_after = df[c].isna().sum()

                    col_elapsed = time.perf_counter() - col_start  # ⏱️ end timing
                    logw(f"Column '{c}': mode = '{mode_val}' | Filled {missing_before - missing_after} "
                        f"missing values | elapsed = {col_elapsed:.4f}s")
                    logw(log_memory(f"[DATA IMPUTATION - {c}]"))
                else:
                    logw(f"Column '{c}': No valid mode found — skipped.")
            except Exception as e:
                logw(f"Column '{c}': mode calculation failed — {str(e)}")

        step_elapsed = time.perf_counter() - step_start

        logw(f"[STEP fill_missing in categorical] Completed in {time.perf_counter()-start_cat:.4f} seconds "
            f"(cat_cols={len(cat_cols)})")
        logw(log_memory(f"[DATA IMPUTATION CATEGORICAL OVERALL]"))

        logw(f"[STEP fill_missing] Completed in {step_elapsed:.4f} seconds "
            f"(numeric_cols={len(num_cols)}, cat_cols={len(cat_cols)})\n\n")
        

        # --------------------------------------------------------------------
        # STEP 8: Handle Outliers (IQR capping)
        # --------------------------------------------------------------------
        step_start = time.perf_counter()
        logw("[STEP outlier_capping] --- Starting outlier handling ---")
        for c in num_cols:
            col_start = time.perf_counter()  # ⏱️ start timing for this column

            q1, q3 = df[c].quantile(0.25), df[c].quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outliers = ((df[c] < lower) | (df[c] > upper)).sum()
            df[c] = np.where(df[c] < lower, lower, np.where(df[c] > upper, upper, df[c]))

            col_elapsed = time.perf_counter() - col_start  # ⏱️ end timing
            logw(f"Column '{c}': capped {outliers} outliers "
                 f"(bounds=({lower:.4f}, {upper:.4f})) | elapsed={col_elapsed:.4f}s")
            logw(log_memory(f"OUTLIER HANDLING - {c}"))
            
        logw(f"[STEP outlier_capping] Completed in {time.perf_counter() - step_start:.4f}s\n")
        logw(log_memory(f"[OUTLIER HANDLING OVERALL]"))

        # --------------------------------------------------------------------
        # STEP 9: Normalization + Standardization (new columns)
        # --------------------------------------------------------------------
        step_start = time.perf_counter()
        scaler_norm = MinMaxScaler()
        scaler_std = StandardScaler()
        for c in num_cols:
            col_start = time.perf_counter()  # ⏱️ start timing for this column


            col_data = df[[c]].values.astype(float)
            df[f"{c}_norm"] = scaler_norm.fit_transform(col_data)
            df[f"{c}_std"] = scaler_std.fit_transform(col_data)

            col_elapsed = time.perf_counter() - col_start  # ⏱️ end timing
            logw(f"Column '{c}': normalized -> '{c}_norm', standardized -> '{c}_std' | elapsed={col_elapsed:.4f}s")
            logw(log_memory(f"[NORM STAND - {c}]"))
        
        logw(f"[STEP scale_features] {time.perf_counter() - step_start:.4f}s\n")
        logw(log_memory(f"[NORM STAND - OVERALL]"))

        # --------------------------------------------------------------------
        # STEP 10: Encode Categorical Columns (Label + One-hot)
        # --------------------------------------------------------------------
        # step_start = time.perf_counter()
        # le = LabelEncoder()
        # for c in cat_cols:
        #     try:
        #         col_start = time.perf_counter()  # ⏱️ start timing for this column

        #         df[f"{c}_encoded"] = le.fit_transform(df[c].astype(str))
        #         ohe = pd.get_dummies(df[c], prefix=c)
        #         df = pd.concat([df, ohe], axis=1)

        #         col_elapsed = time.perf_counter() - col_start  # ⏱️ end timing
        #         logw(f"Column '{c}': label + one-hot encoded ({len(ohe.columns)} cols added) | elapsed={col_elapsed:.4f}s")
        #     except Exception as e:
        #         logw(f"Column '{c}': encoding failed — {e}")
        # logw(f"[STEP encode_categorical] {time.perf_counter() - step_start:.4f}s\n")

        # --- STEP 6: drop duplicates ---
        step_start = time.perf_counter()
        before = len(df)
        df = df.drop_duplicates()
        after = len(df)
        step_elapsed = time.perf_counter() - step_start
        logw(f"[STEP drop_duplicates] elapsed_s={step_elapsed:.4f} rows_before={before} rows_after={after}\n\n")
        logw(log_memory(f"[DROP DUPLICATES]"))

        # --- STEP 7: save cleaned CSV ---
        step_start = time.perf_counter()
        df.to_csv(args.out, index=False)
        step_elapsed = time.perf_counter() - step_start
        logw(f"[STEP save_csv] elapsed_s={step_elapsed:.4f} saved_to={args.out}\n\n")
        logw(log_memory(f"[DROP DUPLICATES]"))


        # stop monitor and compute peak memory
        overall_elapsed = time.perf_counter() - overall_start
        stop_event.set()
        monitor.join(timeout=2.0)
        peak_rss = max(mem_samples) if mem_samples else 0

        logw(f"{'='*10} SUMMARY {'='*10}")
        logw(f"Total elapsed (wall clock) = {overall_elapsed:.4f} s")
        logw(f"Peak RSS observed (bytes) = {peak_rss:,}")
        logw(f"Final shape rows={len(df)} cols={len(df.columns)}")
        logw(log_memory(f"[END]"))
        logw(f"End time: {time.ctime()}")

if __name__ == "__main__":
    main()
