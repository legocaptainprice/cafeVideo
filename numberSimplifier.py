# This simplifies views beyond 1,000 to 1K, 10K, 100K, 1M, and so on.

def viewSimplify(viewCount):
    if viewCount is None:
        return 0

    units = ["", "K", "M", "B", "T"]  # the unit of the digit
    index = 0

    while viewCount >= 1000 and index < len(units) - 1:  # if the viewCount is greater than 1000, keep cutting off last 3 digits
        viewCount //= 1000
        index += 1

    return f"{viewCount}{units[index]}"
