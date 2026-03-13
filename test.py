def validate(x: int) -> bool:
    data = set()
    for i in range(9, -1, -1):
        a = x // (10**i)
        data.add(a % (10 - i))
        if a % (10 - i) != 0:
            return False
    return len(data) == 10


map = list(range(0, 10))


if __name__ == "__main__":
    main()
