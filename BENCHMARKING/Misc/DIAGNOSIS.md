# Diagnosis: Why POST/PUT/DELETE Fail in Rust Benchmarks

## Observed Failures
- CREATE (POST) /api/create: ✅ Success (200/200)
- READ (GET) /api/read: ✅ Success (200/200)  
- READ SINGLE (GET) /api/read/:id: ❌ Failure (0/100) — all failed
- UPDATE (PUT) /api/update/:id: ❌ Failure (0/100) — all failed
- DELETE: ❌ Failure (0/100) — all failed

## Root Cause

Your original PowerShell commands used escaped quotes and backslashes in URLs like:
```powershell
python 'C:\Users\pm018586\Downloads\benchmarks\bench.py' --method GET --url \"http://127.0.0.1:3000/api/read/$firstId\" ...
```

**The issue:**
1. `\"` before and after the URL tells PowerShell to print literal backslash-quote characters.
2. When PowerShell expands `$firstId` inside double quotes with leading `\`, the resulting URL sent to `bench.py` is malformed.
3. For example, if `$firstId = "3a2e5655-34b0-4176-a94b-bc71050644e8"`, the URL becomes:
   ```
   \http://127.0.0.1:3000/api/read/3a2e5655-34b0-4176-a94b-bc71050644e8\
   ```
   (with leading/trailing backslashes)
4. `requests` sends this malformed URL to the server, which doesn't match any routes → 404 or connection failure → benchmark records "Failure".

## Solutions

### Solution 1: Use Proper PowerShell Quoting (RECOMMENDED)

Use double quotes for the URL string (without leading `\`) and single quotes for JSON data:

```powershell
# Correct: double quotes around URL (no leading backslash)
python 'C:\Users\pm018586\Downloads\benchmarks\bench.py' --method GET --url "http://127.0.0.1:3000/api/read/$firstId" -c 5 -n 100 -o "C:\Users\pm018586\Downloads\benchmarks\rust\rust_readone_baseline.csv" --monitor-pid $rustPid --include-client-latency

# Correct: single quotes around JSON data (prevents backslash interpretation)
python 'C:\Users\pm018586\Downloads\benchmarks\bench.py' --method PUT --url "http://127.0.0.1:3000/api/update/$firstId" -H 'Content-Type: application/json' --data '{"name":"updated","description":"u"}' -c 5 -n 100 ...
```

### Solution 2: Use Diagnostic Flag

To verify the exact URL/data being sent to the Rust server, add `--verbose-first-request` flag:

```powershell
python 'C:\Users\pm018586\Downloads\benchmarks\bench.py' --method GET --url "http://127.0.0.1:3000/api/read/$firstId" -c 5 -n 10 --verbose-first-request
```

This will print:
```
[DIAGNOSTIC] Method: GET
[DIAGNOSTIC] URL: http://127.0.0.1:3000/api/read/3a2e5655-34b0-4176-a94b-bc71050644e8
[DIAGNOSTIC] Data: None
[DIAGNOSTIC] Headers: {}
[DIAGNOSTIC] Concurrency: 5, Requests: 10
```

If you see leading/trailing backslashes or garbled characters, the URL quoting is wrong.

### Solution 3: Escape Variables in PowerShell

If you must use escaped quotes, escape the dollar sign:

```powershell
# Alternative (but not recommended): escape the variable
$url = "http://127.0.0.1:3000/api/read/$firstId"
python 'C:\Users\pm018586\Downloads\benchmarks\bench.py' --method GET --url $url -c 5 -n 100
```

## Updated Commands

See `CORRECTED_COMMANDS.txt` in the same directory for the full set of corrected benchmarking commands:
- Uses proper quoting (double quotes for URLs, single for JSON).
- Includes diagnostic output where needed.
- All commands structured to avoid PowerShell escape issues.

## Key Takeaway

**When passing URLs or JSON to `bench.py` from PowerShell:**
- Use **double quotes** for URLs with variables: `--url "http://.../$variable"`
- Use **single quotes** for JSON strings: `--data '{"key":"value"}'`
- Do **NOT** use leading backslashes before quoted strings: ❌ `\"http://...\"` → use ✅ `"http://..."` instead.

## Next Steps

1. Run the corrected commands from `CORRECTED_COMMANDS.txt`.
2. If you still see failures, add `--verbose-first-request` to one of the failing tests to see what URL is actually being sent.
3. The Flask benchmarks should follow the same quoting rules.
