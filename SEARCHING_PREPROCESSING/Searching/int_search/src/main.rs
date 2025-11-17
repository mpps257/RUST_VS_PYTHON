#![allow(unused)]

const ARRAY_SIZE : usize = 10_00_000;
const MIN : i32 = 1000;
const MAX : i32 = 10000;

use std::{time::Instant, fs::File};
use sysinfo::{Pid, System};
use std::cmp::Ordering;
 
//Random value generation
use rand::Rng;

fn process_info(sys: &mut System, pid: Pid,print_log: String, start_time: &Instant) {
    println!("============={}================",print_log);
    sys.refresh_all();
    if let Some(process) = sys.process(pid) {
        println!("Process name: {}", process.name());
        println!("Executable path: {:?}", process.exe());
        println!("Memory usage: {:.2} MB", process.memory() as f64 / 1024.0 / 1024.0);
    } else {
        println!("Process not found!");
    }
    println!("Till -- {} : {:#?}",print_log,start_time.elapsed());
}


fn generate_sorted_random_array(n: usize) -> Vec<i32> {
    let mut rng = rand::thread_rng();
    let mut arr: Vec<i32> = (0..n).map(|_| rng.gen_range(MIN..MAX)).collect();
    arr.sort();
    arr
}

fn interpolation_search(arr: &[i32], target: i32) -> Option<usize> {
    let mut low = 0usize;
    let mut high = arr.len() - 1;

    while low <= high && arr[low] <= target && arr[high] >= target {
        if arr[high] == arr[low] {
            if arr[low] == target {
                return Some(low);
            } else {
                return None;
            }
        }
        let pos = low + (((high - low) as f64 * 
            (target - arr[low]) as f64 / (arr[high] - arr[low]) as f64) as usize);
        if arr[pos] == target {
            return Some(pos);
        } else if arr[pos] < target {
            low = pos + 1;
        } else {
            if pos == 0 { break; }
            high = pos - 1;
        }
    }
    None
}

fn main() {
    
    // Start timer
    let start_time = Instant::now();

    // Initialize system info
    let mut sys = System::new_all();
    sys.refresh_all();

    // Get current process ID
    let pid = sysinfo::get_current_pid().unwrap();
    process_info(&mut sys, pid,String::from("Before Interpolation Search"),&start_time);

    //=====================================================================================================
    let sorted_array = generate_sorted_random_array(ARRAY_SIZE);
    //println!("{:?}", sorted_array);
    process_info(&mut sys, pid,String::from("Array Generation & Sort"),&start_time);

    let first = &sorted_array[0];
    let last = &sorted_array[ARRAY_SIZE - 1];
    let middle = &sorted_array[ARRAY_SIZE/2];
    let el_les = 50;
    let el_grt = 10006;
    println!(
        "First : {} , Last : {} , Middle : {} , Element < MIN : {} , Element > MAX {}",
        first,
        last,
        middle,
        el_les,
        el_grt);
    //=====================================================================================================
    println!("Interpolation Search First Element : {:#?}",interpolation_search(&sorted_array,*first).unwrap());
    process_info(&mut sys, pid,String::from("First Element Search"),&start_time);
    println!("Interpolation Search Last Element : {:#?}",interpolation_search(&sorted_array,*last).unwrap());
    process_info(&mut sys, pid,String::from("Last Element Search"),&start_time);
    println!("Interpolation Search Middle Element : {:#?}",interpolation_search(&sorted_array,*middle).unwrap());
    process_info(&mut sys, pid,String::from("Middle Element Search"),&start_time);

    println!("=================================");
    println!("Interpolation Search Element < {MIN} : {:#?}",interpolation_search(&sorted_array,el_les));
    process_info(&mut sys, pid,String::from("Element < MIN Search"),&start_time);
    
    println!("=================================");
    println!("Interpolation Search Element > {MAX} : {:#?}",interpolation_search(&sorted_array,el_grt));
    process_info(&mut sys, pid,String::from("Element > MAX Search"),&start_time);
    
}