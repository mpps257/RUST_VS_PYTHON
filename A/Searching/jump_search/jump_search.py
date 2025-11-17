import random
import math

MIN = 1000
MAX = 10000
ARRAY_SIZE = 10_00_000
@profile
def generate_sorted_random_array(n: int) -> list[int]:
    arr = [random.randint(MIN, MAX) for _ in range(n)]
    arr.sort()
    return arr

@profile
def jump_search(arr, target):
    n = len(arr)
    step = int(math.sqrt(n))
    prev = 0
    while arr[min(step, n) - 1] < target:
        prev = step
        step += int(math.sqrt(n))
        if prev >= n:
            return -1
    for i in range(prev, min(step, n)):
        if arr[i] == target:
            return i
    return -1

@profile
def main():
    array = generate_sorted_random_array(ARRAY_SIZE)
    first = array[0]
    last = array[-1]
    middle = array[ARRAY_SIZE//2]
    el_les = 50
    el_grt = 100006
    print(f"First : {first} , Last : {last} , Middle : {middle} , Element < MIN : {50} , Element > MAX {100006}")

    print(f"Jump Search First Element : {jump_search(array,first)}")
    print(f"Jump Search Last Element : {jump_search(array,last)}")
    print(f"Jump Search Middle Element : {jump_search(array,middle)}")
    print(f"Jump Search Element < {MIN}  : {jump_search(array,el_les)}")
    print(f"Jump Search Element > {MAX}  : {jump_search(array,el_grt)}")

if __name__ == "__main__":
    main()