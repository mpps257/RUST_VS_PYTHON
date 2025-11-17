#!/usr/bin/env python3
"""
compare_benchmarks.py
Usage:
  python compare_benchmarks.py --rust rust_benchmark.xlsx --py python_benchmark.xlsx --out report_dir
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import json
import math

sns.set(style="whitegrid")

OP_KEYWORDS = {
    'create': ['create'],
    'read_all': ['read_all', 'read-all', r'(^|_)read($|_)', r'\bread\b'],
    'read_one': ['readone','read_one','read-one','readone_baseline'],
    'update': ['update'],
    'delete': ['delete']
}

def infer_operation(sheet_name: str):
    name = sheet_name.lower()
    for op, kwlist in OP_KEYWORDS.items():
        for kw in kwlist:
            if re.search(kw, name):
                return op
    # fallback: try basic words
    if 'create' in name: return 'create'
    if 'update' in name: return 'update'
    if 'delete' in name: return 'delete'
    if 'readone' in name or 'read_one' in name or '_readone' in name: return 'read_one'
    if 'read' in name: return 'read_all'
    return 'other'

def read_sheets(excel_path: Path):
    x = pd.ExcelFile(excel_path, engine='openpyxl')
    sheets = {}
    for sheet in x.sheet_names:
        df = x.parse(sheet)
        # normalize columns
        df.columns = [c.lower() for c in df.columns]
        # try to coerce latency
        if 'latency_ms' in df.columns:
            df['latency_ms'] = pd.to_numeric(df['latency_ms'], errors='coerce')
        # ensure success exists
        if 'success' in df.columns:
            df['success'] = pd.to_numeric(df['success'], errors='coerce').fillna(0).astype(int)
        sheets[sheet] = df
    return sheets

def summarize_df(df: pd.DataFrame):
    total = len(df)
    successes = int(df['success'].sum()) if 'success' in df.columns else int((df.get('status_code', pd.Series()).between(200,299)).sum())
    failures = total - successes
    lat = df['latency_ms'].dropna() if 'latency_ms' in df.columns else pd.Series(dtype=float)
    def q(p): return float(lat.quantile(p)) if len(lat)>0 else math.nan
    return {
        'n': total,
        'successes': successes,
        'failures': failures,
        'mean_ms': float(lat.mean()) if len(lat)>0 else math.nan,
        'p50_ms': q(0.50),
        'p95_ms': q(0.95),
        'p99_ms': q(0.99),
        'min_ms': float(lat.min()) if len(lat)>0 else math.nan,
        'max_ms': float(lat.max()) if len(lat)>0 else math.nan,
    }

def aggregate_by_operation(sheets: dict):
    ops = {}
    for sheet_name, df in sheets.items():
        op = infer_operation(sheet_name)
        ops.setdefault(op, []).append((sheet_name, df))
    return ops

def collate_latencies(op_list):
    # op_list: list of (sheetname, df)
    lat = []
    for name, df in op_list:
        if 'latency_ms' in df.columns:
            lat.extend(df['latency_ms'].dropna().tolist())
    return np.array(lat)

def plot_latency_cdf(two_series: dict[str, np.ndarray], out_path: Path, title='Latency CDF'):
    plt.figure(figsize=(8,5))
    for label, arr in two_series.items():
        if len(arr) == 0: continue
        s = np.sort(arr)
        y = np.arange(1, len(s)+1) / len(s)
        plt.plot(s, y, label=label)
    plt.xlabel('Latency (ms)')
    plt.ylabel('CDF')
    plt.legend()
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

def plot_boxplot(data: pd.DataFrame, x, y, out_path, title=''):
    plt.figure(figsize=(8,5))
    sns.boxplot(x=x, y=y, data=data)
    plt.xticks(rotation=30)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

def mannwhitney(u_sample_a, u_sample_b):
    if len(u_sample_a) < 2 or len(u_sample_b) < 2:
        return np.nan, np.nan
    try:
        stat, p = stats.mannwhitneyu(u_sample_a, u_sample_b, alternative='two-sided')
        # compute rank-biserial effect size roughly
        n1 = len(u_sample_a); n2 = len(u_sample_b)
        # common transformation: r = z / sqrt(N) ; approximate z from stat
        # use normal approximation
        mean_u = n1*n2/2.0
        std_u = math.sqrt(n1*n2*(n1+n2+1)/12.0)
        z = (stat - mean_u) / std_u
        r = z / math.sqrt(n1+n2)
        return p, r
    except Exception:
        return np.nan, np.nan

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rust', required=True)
    p.add_argument('--py', required=True)
    p.add_argument('--out', default='cmp_report')
    args = p.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rust_sheets = read_sheets(Path(args.rust))
    py_sheets = read_sheets(Path(args.py))

    rust_ops = aggregate_by_operation(rust_sheets)
    py_ops = aggregate_by_operation(py_sheets)

    # build summary
    summary_rows = []
    operations = sorted(set(list(rust_ops.keys()) + list(py_ops.keys())))
    for op in operations:
        rust_lat = collate_latencies(rust_ops.get(op, []))
        py_lat = collate_latencies(py_ops.get(op, []))
        # stats
        rust_stats = summarize_df(pd.concat([df for _, df in rust_ops.get(op, [])], ignore_index=True)) if rust_ops.get(op) else {}
        py_stats = summarize_df(pd.concat([df for _, df in py_ops.get(op, [])], ignore_index=True)) if py_ops.get(op) else {}
        pval, eff = mannwhitney(rust_lat, py_lat)
        summary_rows.append({
            'operation': op,
            'rust_n': rust_stats.get('n', 0),
            'py_n': py_stats.get('n', 0),
            'rust_mean_ms': rust_stats.get('mean_ms', math.nan),
            'py_mean_ms': py_stats.get('mean_ms', math.nan),
            'rust_p50_ms': rust_stats.get('p50_ms', math.nan),
            'py_p50_ms': py_stats.get('p50_ms', math.nan),
            'rust_p95_ms': rust_stats.get('p95_ms', math.nan),
            'py_p95_ms': py_stats.get('p95_ms', math.nan),
            'rust_successes': rust_stats.get('successes', 0),
            'py_successes': py_stats.get('successes', 0),
            'pvalue_mwu': pval,
            'effect_r': eff
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(out_dir / 'comparison_summary.csv', index=False)

    # Combined latency CDF for all operations (one plot per operation)
    for op in operations:
        rust_lat = collate_latencies(rust_ops.get(op, []))
        py_lat = collate_latencies(py_ops.get(op, []))
        if len(rust_lat)==0 and len(py_lat)==0:
            continue
        plot_latency_cdf({'rust': rust_lat, 'python': py_lat}, out_dir/f'cdf_{op}.png', title=f'Latency CDF - {op}')

    # Boxplot across operations: build combined dataframe
    records = []
    for op in operations:
        for name, df in rust_ops.get(op, []):
            if 'latency_ms' in df.columns:
                for v in df['latency_ms'].dropna():
                    records.append({'operation': op, 'impl': 'rust', 'latency_ms': v})
        for name, df in py_ops.get(op, []):
            if 'latency_ms' in df.columns:
                for v in df['latency_ms'].dropna():
                    records.append({'operation': op, 'impl': 'python', 'latency_ms': v})
    if records:
        comb = pd.DataFrame(records)
        # per-op boxplot grouped by implementation
        plt.figure(figsize=(12,6))
        sns.boxplot(x='operation', y='latency_ms', hue='impl', data=comb)
        plt.yscale('log')  # helpful for heavy-tail latency
        plt.title('Latency by operation: Rust vs Python (log-scale)')
        plt.tight_layout()
        plt.savefig(out_dir/'boxplot_by_op.png')
        plt.close()

    # save a short markdown summary
    md_lines = ['# Benchmark Comparison', '', f'Generated: {pd.Timestamp.now()}', '', '## Summary CSV', '', '- comparison_summary.csv', '', '## Plots', '']
    for f in sorted(out_dir.glob('*.png')):
        md_lines.append(f'- ![]({f.name})')
    (out_dir/'REPORT.md').write_text('\n'.join(md_lines), encoding='utf-8')
    print('Report generated in', out_dir)

if __name__ == '__main__':
    main()