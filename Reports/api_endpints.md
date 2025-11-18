# Compare API endpoint: Python(Flask) vs Rust(Axum)
![Rust Vs Python](images/RS_VS_PY.png)


This report presents a comprehensive quantitative comparison of how quick tasks are done when we use web frameworks and Api endpoints in Python and Rust, focusing on performance metrics including execution time, memory utilization, and scalability characteristics.

---

## 1. Introduction

### 1.1 Overview
This study compares web framework implementations in two different programming languages:


- **Python**: A high-level, interpreted language known for ease of development. Here we are using **Flask** API calls.
- **Rust**: A systems programming language emphasizing performance and memory safety. This is compiler based. Here we are using **Axum** API calls

### 1.2 Objectives
- Measure and compare execution time for preprocessing operations
- Analyze memory consumption patterns
- Evaluate scalability characteristics under varying data loads with bulk operations
- Check for latency comparisons between Raw SQL code and ORM.

---

## 2. Experimental Setup

### 2.1 Environment Configuration
The experiments were conducted under controlled conditions to ensure reproducibility and fair comparison between both implementations. Isolated execution to minimize external interference. Similar approach is followed for further comparisons also.

- Python implementation with standard Flask framework.
- Rust implementation with Axum web framework.
- Indentical endpoint implementations are done

### 2.2 Methodology
The experimental approach included:
- Multiple test iterations are done and results are averaged accross them.
- Comparisons done on fixed number of requests to the web application created.


---

## 3. Time Profiling Comparison

### 3.1 CRUD Operations Execution Latencies

The time profiling analysis reveals significant performance differences between Python and Rust implementations during the preprocessing phase.

**Key Findings:**
- Rust demonstrates consistently faster preprocessing times
- Python shows higher execution overhead due to interpreted nature and also since Flask is sequential adds additional overhead

### 3.2 Performance Analysis
![Mean Latency Comparison](images/mean%20latency%20comparison.png)

- Each of the requests were made for certain number of time 
- Collected latencies are averaged and plotted for comparison
- Can observe that for tasks which are requiring access to the backend database require more time.
- We can see Python was drastically slow when compared to Rust

**P95** **(95th percentile)** **latency**: 95% of all requests completed faster than this value, and 5% were slower.It captures how your API behaves under real-world load, especially for the slower requests. 

![Tail Latency Comparison](images/p95%20latency%20comparison.png)
- Reveals that reads and deletes are little unstable in case of Rust 
- Nevertheless Rust outperforms Python in tail latency comparison.

**Throughput Comparison**
- Reveals the number of tasks or requests that can be processed in a unit time. So lower the execution time better the processing speed. Hence Rust does well in this case too in line with what we have observed in cases of mean latency and tail latency comparison.
- Since we mentioned already about unstability in processing the Reads and Deletes we can observe a little lower throughput. 

![Throughput Comparison](images/Throughput%20comparison.png)


## 4. Memory Profiling

### 4.1 Memory Consumption Patterns

Memory profiling reveals distinct characteristics in how each handles requests and amount of space occupied and also amount of variability on bulk requests for memory intensive tasks:
![Memory Endpoint comparison](images/Memory%20Endpoint.png)

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
- No huge variability observed both of them vary **~0.5MB**


---

## 5. Scalability Analysis

### 5.1 Scaling Characteristics

Scalability testing examined how both implementations handle increasing data volumes during when we have bulk requests.

| Operation | Python | Rust |
|----------------|------------------|------|
| **Create** | ~1396 ms | ~625 ms |
| **Read** | ~255 ms | ~50.5 ms |
| **Update** | ~822.9 ms | ~283.54 ms |
| **Delete** | ~1050.4 ms | ~35.05 ms |

### 5.2 ORM vs RAW SQL

The memory usage lied in this range for all the CRUD operations
| Framework | Memory Usage |
|----------|--------------|
| **Python (Flask – RAW SQL)** | ~40-45 MB |
| **Python (Flask – ORM)** | ~71-75 MB |
| **Rust (Axum - RAW SQL)** | ~25-32 MB |
| **Rust (Axum - Sea_ORM)** | ~58-62 MB |

- In all the CRUD operations ORM was taking always greater amount of time major reason being the additional abstraction layer added.
---

## 6. Conclusions

### Key Findings

1. **Performance**: Rust significantly outperforms Python in CRUD operations in comparison of web frameworks. But was observed to be unstable in reads and deletes
2. **Memory Efficiency**: Rust demonstrates lower and more predictable memory usage
3. **Scalability**: Rust scales more effectively for large workloads and is proportionate to average latency which is an evidence for its predictability.
4. **Development Trade-offs**: Python offers faster development at the cost of runtime performance

**Choose Rust When:**
- Performance is critical
- Working with large datasets and memory constraints
- Building production-scale systems

**Choose Python When:**
- Simplified code and rapid prototyping is priority
- Development time is constrained
- Leveraging extensive library ecosystem
