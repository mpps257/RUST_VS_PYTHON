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
def interpolation_search(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high and arr[low] <= target <= arr[high]:
        if arr[high] == arr[low]:
            if arr[low] == target:
                return low
            else:
                return -1
        pos = low + int(((float(high - low) / (arr[high] - arr[low])) * (target - arr[low])))
        if arr[pos] == target:
            return pos
        elif arr[pos] < target:
            low = pos + 1
        else:
            high = pos - 1
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

    print(f"Jump Search First Element : {interpolation_search(array,first)}")
    print(f"Jump Search Last Element : {interpolation_search(array,last)}")
    print(f"Jump Search Middle Element : {interpolation_search(array,middle)}")
    print(f"Jump Search Element < {MIN}  : {interpolation_search(array,el_les)}")
    print(f"Jump Search Element > {MAX}  : {interpolation_search(array,el_grt)}")

if __name__ == "__main__":
    main()