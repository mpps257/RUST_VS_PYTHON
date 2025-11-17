#![allow(unused)]

use std::{fs::File, time::Instant};
use sysinfo::{Pid, System};

use anyhow::Result;
use polars::prelude::*;
use rand::seq::SliceRandom;
use rand::thread_rng;
use std::collections::HashMap;

fn process_info(sys: &mut System, pid: Pid, print_log: String, start_time: &Instant) {
    //println!("============={}================",print_log);
    sys.refresh_all();
    if let Some(process) = sys.process(pid) {
        println!("Process name: {}", process.name());
        println!("Executable path: {:?}", process.exe());
        println!(
            "Memory usage: {:.2} MB",
            process.memory() as f64 / 1024.0 / 1024.0
        );
    } else {
        println!("Process not found!");
    }
    println!("Till -- {} : {:#?}", print_log, start_time.elapsed());
}

fn load_csv(path: &str) -> Result<DataFrame> {
    let file = File::open(path).unwrap();
    let df = CsvReader::new(file).finish().unwrap();
    Ok(df)
}

fn get_column_types(df: &DataFrame) -> (Vec<String>, Vec<String>) {
    let mut num_cols = Vec::new();
    let mut cat_cols = Vec::new();

    for field in df.schema().iter_fields() {
        match field.dtype() {
            //For numerical datatypes
            DataType::Float32 | DataType::Float64 | DataType::Int32 | DataType::Int64 => {
                num_cols.push(field.name().to_string());
            }

            //For categorical datatypes
            DataType::String => {
                cat_cols.push(field.name().to_string());
            }

            //Default data
            _ => {}
        }
    }
    (num_cols, cat_cols)
}

fn column_most_missing(df: &DataFrame, columns: &[String]) -> Option<String> {
    let mut max_missing = 0;
    let mut best_col = None;

    for col in columns {
        if let Ok(series) = df.column(col) {
            let missing = series.null_count();
            if missing > max_missing {
                max_missing = missing;
                best_col = Some(col.clone());
            }
        }
    }
    best_col
}

fn impute_numerical(df: &mut DataFrame, column: &str, strategy: &str) -> PolarsResult<()> {
    let new_col = format!("{}_imputed_{}", column, strategy);

    // Fill nulls and create new series
    let filled_series = match df.column(column)? {
        s if s.dtype().is_numeric() => {
            let mut filled = s.fill_null(match strategy {
                "mean" => FillNullStrategy::Mean,
                "min" => FillNullStrategy::Min,
                _ => FillNullStrategy::Zero,
            })?;
            filled.rename((&new_col).into()); // rename in place
            filled // return the series
        }
        _ => {
            return Err(PolarsError::ComputeError(
                format!(
                    "Unsupported dtype {:?} for imputation",
                    df.column(column)?.dtype()
                )
                .into(),
            ))
        }
    };

    df.with_column(filled_series)?;
    Ok(())
}

// fn process_categorical(
//     df: &DataFrame,
//     column: &str,
//     fill_strategy: &str,
//     encode: bool,
//     to_upper: bool,
// ) -> Result<(DataFrame, String)> {
//     let mut df = df.clone();
//     let new_col = format!("{}_processed", column);
//     let s = df.column(column)?.utf8()?;

//     let mode_val = s.mode().get(0).cloned().unwrap_or("UNKNOWN".to_string());
//     let mut filled = s.fill_null(FillNullStrategy::Literal(AnyValue::Utf8(&mode_val)))?;

//     if to_upper {
//         filled = filled.apply(|opt| opt.map(|v| v.to_uppercase()).map(|s| s.into())).utf8()?;
//     }

//     let mut final_series = filled.into_series();
//     if encode {
//         final_series = final_series.cast(&DataType::Categorical(None))?;
//     }

//     df.with_column(final_series.rename(&new_col))?;
//     Ok((df, new_col))
// }

fn normalize_column(df: &mut DataFrame, column: &str, method: &str) -> PolarsResult<()> {
    let s = df.column(column)?.f64()?;
    let new_col = format!("{}_normalized_{}", column, method);

    let mut norm = match method {
        "minmax" => {
            let min = s.min().unwrap();
            let max = s.max().unwrap();
            //println!("Normalizing '{}' with minmax: min={:.4}, max={:.4}", column, min, max);
            s.apply(|opt| opt.map(|v| (v - min) / (max - min)))
                .into_series()
        }
        // "zscore" => {
        //     let mean = s.mean().unwrap();
        //     let std = s.std_as_series(1).f64()?.get(0).unwrap();
        //     //println!("Normalizing '{}' with zscore: mean={:.4}, std={:.4}", column, mean, std);
        //     s.apply(|opt| opt.map(|v| (v - mean) / std)).into_series()
        // }
        _ => {
            //println!("Unknown method '{}', no normalization applied", method);
            s.clone().into_series()
        }
    };

    norm.rename((&new_col).into());
    df.with_column(norm)?;

    Ok(())
}

// fn convert_type(df: &DataFrame, column: &str, dtype: DataType) -> Result<(DataFrame, String)> {
//     let mut df = df.clone();
//     let new_col = format!("{}_as_{:?}", column, dtype);
//     let converted = df.column(column)?.cast(&dtype)?;
//     df.with_column(converted.rename(&new_col))?;
//     Ok((df, new_col))
// }

fn add_column(
    df: &mut DataFrame,
    new_col: &str,
    source_col: &str,
    op: fn(f64) -> f64,
) -> PolarsResult<()> {
    let s = df.column(source_col)?.f64()?;
    let mut derived = s.apply(|opt| opt.map(op)).into_series();
    derived.rename(new_col.into());
    df.with_column(derived)?;
    Ok(())
}

fn filter_rows(df: &mut DataFrame, column: &str) -> PolarsResult<()> {
    let mask = df.column(column)?.f64()?.gt(0.0);
    *df = df.filter(&mask)?;
    Ok(())
}

// fn rename_columns(df: &DataFrame, mapping: HashMap<&str, &str>) -> Result<DataFrame> {
//     let mut df = df.clone();
//     for (old, newn) in mapping {
//         df = df.rename(old, newn)?;
//     }
//     Ok(df)
// }

// fn aggregate_df(df: &DataFrame, group_col: &str, agg_col: &str) -> Result<DataFrame> {
//     let gb = df.groupby([group_col])?;
//     Ok(gb.select([agg_col]).mean()?)
// }

fn select_drop_columns(
    df: &DataFrame,
    select: Option<&[&str]>,
    drop: Option<&[&str]>,
) -> PolarsResult<DataFrame> {
    let mut df = df.clone();
    if let Some(cols) = select {
        let col_vec: Vec<&str> = cols.iter().map(|&c| c).collect();
        df = df.select(col_vec)?;
    }
    if let Some(cols) = drop {
        for &c in cols {
            df = df.drop(c)?;
        }
    }
    Ok(df)
}

fn sample_df(df: &DataFrame, frac: f64) -> Result<DataFrame> {
    let n = (df.height() as f64 * frac).round() as usize;
    let mut indices: Vec<usize> = (0..df.height()).collect();
    indices.shuffle(&mut thread_rng());
    let take = &indices[..n];
    Ok(df.take(&UInt32Chunked::from_vec(
        "idx".into(),
        take.iter().map(|&x| x as u32).collect(),
    ))?)
}

fn full_preprocessing_pipeline(path: &str) -> Result<()> {
    //println!("Starting preprocessing pipeline...");

    // Start timer
    let start_time = Instant::now();

    // Initialize system info
    let mut sys = System::new_all();
    sys.refresh_all();

    // Get current process ID
    let pid = sysinfo::get_current_pid().unwrap();
    process_info(
        &mut sys,
        pid,
        String::from("Initial Process info"),
        &start_time,
    );

    //===================================================================================================================
    let mut df = load_csv(path)?;
    let (rows, cols) = df.shape();
    //println!("DataFrame shape: ({}, {})", rows, cols);
    process_info(
        &mut sys,
        pid,
        String::from("After Loading CSV"),
        &start_time,
    );
    //===================================================================================================================
    /*
    for field in df.schema().iter_names_and_dtypes() {
        //println!("{:#?}", field);
    }
    */

    let mut df = df
        .lazy()
        .with_column(col("BENE_DEATH_DT").cast(DataType::Float64))
        .collect()?;

    process_info(
        &mut sys,
        pid,
        String::from("Type Casting \'BENE_DEATH_DT\'"),
        &start_time,
    );

    /*
    for field in df.schema().iter_names_and_dtypes() {
        //println!("{:#?}", field);
    }
    */

    //=======================================================================================================================

    let (num_cols, cat_cols) = get_column_types(&df);
    process_info(
        &mut sys,
        pid,
        String::from("Getting column Types"),
        &start_time,
    );
    // //println!("Numerical Columns : {:#?}",num_cols);
    // //println!("Categorical Columns : {:#?}",cat_cols);

    //=======================================================================================================================

    // For numeric column, we assume at least one exists
    let num_col = column_most_missing(&df, &num_cols)
        .expect("No numeric col found")
        .clone(); // make an owned String

    // For categorical column, handle None safely
    let cat_col: Option<String> = column_most_missing(&df, &cat_cols).map(|col| col.clone()); // clone the &String into owned String

    // Print
    //println!("Numerical column: {}", num_col);

    if let Some(col) = cat_col {
        //println!("Most missing categorical column: {}", col);
    } else {
        //println!("No categorical column found");
    }
    process_info(
        &mut sys,
        pid,
        String::from("Detect most number of missing values"),
        &start_time,
    );

    //=======================================================================================================================

    impute_numerical(&mut df, &num_col, "mean")?;
    process_info(&mut sys, pid, String::from("Imputation"), &start_time);

    //=======================================================================================================================
    // let (df, cat_processed) = process_categorical(&df, &cat_col, "mode", true, true)?;

    let norm_col = String::from("MEDREIMB_CAR");
    normalize_column(&mut df, &norm_col, "minmax")?;
    process_info(&mut sys, pid, String::from("Normalise"), &start_time);
    //=======================================================================================================================
    // let (df, num_as_int) = convert_type(&df, &num_imputed, DataType::Int64)?;

    add_column(&mut df, "column_squared", &norm_col, |v| v * v)?;
    process_info(&mut sys, pid, String::from("Add Column"), &start_time);
    //=======================================================================================================================

    filter_rows(&mut df, &norm_col)?;
    process_info(&mut sys, pid, String::from("Filter"), &start_time);
    //=======================================================================================================================
    let mut df = df
        .sort(
            [&norm_col],
            SortMultipleOptions::new().with_order_descending(false),
        )
        .unwrap();
    process_info(&mut sys, pid, String::from("Sort - Ascending"), &start_time);
    let mut df = df
        .sort(
            [&norm_col],
            SortMultipleOptions::new().with_order_descending(false),
        )
        .unwrap();
    process_info(
        &mut sys,
        pid,
        String::from("Sort - Descending"),
        &start_time,
    );
    //=======================================================================================================================
    let drop_col = String::from("SP_STRKETIA");
    let select_col = String::from("BENE_COUNTY_CD");
    process_info(&mut sys, pid, String::from("Creating Vars"), &start_time);

    let df_selected = select_drop_columns(&mut df, Some(&[&select_col]), None)?;
    process_info(&mut sys, pid, String::from("Column Selection"), &start_time);

    let df_drop = select_drop_columns(&mut df, None, Some(&[&drop_col]))?;
    process_info(&mut sys, pid, String::from("Column Drop"), &start_time);
    //=======================================================================================================================
    let df_sampled = sample_df(&df_selected, 0.1)?;
    process_info(&mut sys, pid, String::from("Sampling"), &start_time);

    // let mut rename_map = HashMap::new();
    // rename_map.insert(num_norm.as_str(), "normalized_value");
    // let df = rename_columns(&df, rename_map)?;
    // let df_agg = aggregate_df(&df, &cat_processed, "normalized_value")?;
    // //println!("✅ Aggregated result:\n{df_agg}");
    // //println!("✅ Sampled subset:\n{df_sampled}");
    Ok(())
}

fn main() -> Result<()> {
    let path = r"C:\Users\pm018586\OneDrive - Zelis Healthcare\Documents\Presentations\Data Preprocessing Python VS Rust\Datasets\176541_DE1_0_2008_Beneficiary_Summary_File_Sample_1\DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv";
    full_preprocessing_pipeline(path)?;
    Ok(())
}
