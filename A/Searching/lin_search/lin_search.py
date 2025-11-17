import random

#1_00_00_000
#2_50_00_000
#5_00_00_000
#10_00_00_000


MIN = 1000
MAX = 10000
ARRAY_SIZE = 10_00_00_000


#@profile
def generate_sorted_random_array(n: int) -> list[int]:
    arr = [random.randint(MIN, MAX) for _ in range(n)]
    arr.sort()
    return arr

#@profile
def linear_search(arr, target):
    for i, val in enumerate(arr):
        if val == target:
            return i
    return -1

#@profile
def main():
    array = generate_sorted_random_array(ARRAY_SIZE)
    first = array[0]
    last = array[-1]
    middle = array[ARRAY_SIZE//2]
    el_les = 50
    el_grt = 100006
    print(f"First : {first} , Last : {last} , Middle : {middle} , Element < MIN : {50} , Element > MAX {100006}")

    print(f"Linear Search First Element : {linear_search(array,first)}")
    print(f"Linear Search Last Element : {linear_search(array,last)}")
    print(f"Linear Search Middle Element : {linear_search(array,middle)}")
    print(f"Linear Search Element < {MIN}  : {linear_search(array,el_les)}")
    print(f"Linear Search Element > {MAX}  : {linear_search(array,el_grt)}")

if __name__ == "__main__":
    main()