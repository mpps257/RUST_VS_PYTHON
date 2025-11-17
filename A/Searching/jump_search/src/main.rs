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


fn jump_search(arr: &[i32], target: i32) -> Option<usize> {
    let n = arr.len();
    let step = (n as f64).sqrt() as usize;
    let mut prev = 0;
    while prev < n && arr[prev.min(n - 1)] < target {
        prev += step;
    }
    let start = prev.saturating_sub(step);
    for i in start..prev.min(n) {
        if arr[i] == target {
            return Some(i as usize);
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
    process_info(&mut sys, pid,String::from("Before Jumpary Search"),&start_time);

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
    println!("Jump Search First Element : {:?}",jump_search(&sorted_array,*first));
    process_info(&mut sys, pid,String::from("First Element Search"),&start_time);
    println!("Jump Search Last Element : {:?}",jump_search(&sorted_array,*last));
    process_info(&mut sys, pid,String::from("Last Element Search"),&start_time);
    println!("Jump Search Middle Element : {:?}",jump_search(&sorted_array,*middle));
    process_info(&mut sys, pid,String::from("Middle Element Search"),&start_time);

    println!("=================================");
    println!("Jump Search Element < {MIN} : {:#?}",jump_search(&sorted_array,el_les));
    process_info(&mut sys, pid,String::from("Element < MIN Search"),&start_time);
    
    println!("=================================");
    println!("Jump Search Element > {MAX} : {:#?}",jump_search(&sorted_array,el_grt));
    process_info(&mut sys, pid,String::from("Element > MAX Search"),&start_time);
    
}