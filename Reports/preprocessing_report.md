# Preprocessing Analysis: Python vs Rust
![Rust Vs Python](images/RS_VS_PY.png)


This report presents a comprehensive quantitative comparison of preprocessing operations implemented in Python and Rust, focusing on performance metrics including execution time, memory utilization, and scalability characteristics.

---

## 1. Introduction

### 1.1 Overview
Preprocessing is a critical phase in data processing pipelines that involves preparing raw data for subsequent analysis and further data tasks. This study compares preprocessing implementations in two different programming languages:


- **Python**: A high-level, interpreted language known for ease of development
- **Rust**: A systems programming language emphasizing performance and memory safety. This is compiler based.

### 1.2 Objectives
- Measure and compare execution time for preprocessing operations
- Analyze memory consumption patterns
- Evaluate scalability characteristics under varying data loads
- Provide evidence-based recommendations for technology selection

---

## 2. Experimental Setup

### 2.1 Environment Configuration
The experiments were conducted under controlled conditions to ensure reproducibility and fair comparison between both implementations. Isolated execution to minimize external interference. Similar approach is followed for further comparisons also.

- Python implementation with standard libraries namely Pandas.
- Rust implementation with optimized compilation flags
- Identical preprocessing algorithms implemented in both languages

### 2.2 Methodology
The experimental approach included:
- Multiple test iterations are done and results are averaged accross them.
- Consistent input datasets across all tests
- Varying dataset sizes to test scalability


---

## 3. Time Profiling Comparison

### 3.1 Preprocessing Execution Times

The time profiling analysis reveals significant performance differences between Python and Rust implementations during the preprocessing phase.

**Key Findings:**
- Rust demonstrates consistently faster preprocessing times
- Python shows higher execution overhead due to interpreted nature
- Performance gap widens with increasing data complexity

### 3.2 Performance Analysis
![Initial Execution Time](images/Execution%20Time%20Comparison%20Rust%20VS%20Python.png)
**Rust Advantages:**
- Initial Observations were that Rust underperforms due to cache misses 
- Hence with a warmup we compared performances of Rust and Python
- Efficient memory management reduces processing delays in case of Rust
- We can see Python was drastically slow when compared to Rust
- Common preprocessing bottlenecks observed was when data parsing and validation operations

**Python Characteristics:**
- Interpreted execution introduces latency
- Dynamic typing adds runtime type-checking overhead
- Higher-level abstractions trade performance for convenience

Following we can see how the whole pipeline execution was much faster in Rust when compared to Python upon warmups

![Warmup And Speedup](images/Warmup%20Pipeline.png)

---

## 4. Memory Profiling

### 4.1 Memory Consumption Patterns

Memory profiling reveals distinct characteristics in how each language handles preprocessing data:
![Warmup And Speedup](images/Memory%20Profiling%20%20Rust%20VS%20Python.png).
![Warmup And Speedup](images/Mem%20Inc%20Comparison.png)


**Rust Memory Profile:**
- Predictable memory allocation patterns
- Deterministic deallocation through ownership system

**Python Memory Profile:**
- Higher baseline memory consumption
- Garbage collection introduces periodic overhead
- Dynamic allocation patterns

**Key Observations:**
- Rust maintains lower memory footprint throughout preprocessing and also has a drop due to memory deallocation
- Python's memory usage shows more variability
- Peak memory usage differs significantly between implementations


---

## 5. Scalability Analysis

### 5.1 Scaling Characteristics

Scalability testing examined how both implementations handle increasing data volumes during preprocessing when we tested using hyperfine.

**Linear Scaling:**
- Both implementations show roughly linear time complexity
- Rust maintains better constant factors 
- Python's overhead becomes more pronounced at scale

**Resource Utilization:**
- Rust scales more efficiently with memory constraints
- Python requires more aggressive resource management at scale

### 5.2 Performance Under Load

As preprocessing workload increases:
- Rust maintains consistent performance characteristics
- Python shows degradation under memory pressure
- Garbage collection impact becomes significant in Python

---

## 6. Conclusions

### Key Findings

1. **Performance**: Rust significantly outperforms Python in preprocessing execution time
2. **Memory Efficiency**: Rust demonstrates lower and more predictable memory usage
3. **Scalability**: Rust scales more effectively for large preprocessing workloads
4. **Development Trade-offs**: Python offers faster development at the cost of runtime performance

**Choose Rust When:**
- Performance is critical
- Working with large datasets and memory constraints
- Building production-scale systems

**Choose Python When:**
- Rapid prototyping is priority
- Development time is constrained
- Leveraging extensive library ecosystem
