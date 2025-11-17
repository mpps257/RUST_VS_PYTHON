import random

MIN = 1000
MAX = 10000
ARRAY_SIZE = 10_00_000
@profile
def generate_sorted_random_array(n: int) -> list[int]:
    arr = [random.randint(MIN, MAX) for _ in range(n)]
    arr.sort()
    return arr

@profile
def binary_search(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
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

    print(f"Bin Search First Element : {binary_search(array,first)}")
    print(f"Bin Search Last Element : {binary_search(array,last)}")
    print(f"Bin Search Middle Element : {binary_search(array,middle)}")
    print(f"Bin Search Element < {MIN}  : {binary_search(array,el_les)}")
    print(f"Bin Search Element > {MAX}  : {binary_search(array,el_grt)}")

if __name__ == "__main__":
    main()