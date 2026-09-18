import math


FEATURE_COUNT = 28
HAND_SCALES = (100.0,) * 5 + (2.0,) * 3 + (250.0,) * 3 + (100.0,) * 3
FEATURE_SCALES = HAND_SCALES + HAND_SCALES


def frame_distance(left, right):
    total = 0.0
    flex_penalty = 0.0
    for index in range(FEATURE_COUNT):
        difference = (left[index] - right[index]) / FEATURE_SCALES[index]
        total += difference * difference
        if index % 14 < 5 and abs(left[index] - right[index]) > 20.0:
            flex_penalty += 0.04
    return math.sqrt(total / FEATURE_COUNT) + flex_penalty


def distance(first, second, window=30):
    rows, columns = len(first), len(second)
    if rows == 0 or columns == 0:
        return float("inf")
    band = max(window, abs(rows - columns))
    previous = [float("inf")] * (columns + 1)
    previous[0] = 0.0
    for row in range(1, rows + 1):
        current = [float("inf")] * (columns + 1)
        start = max(1, row - band)
        end = min(columns, row + band)
        for column in range(start, end + 1):
            cost = frame_distance(first[row - 1], second[column - 1])
            current[column] = cost + min(
                current[column - 1], previous[column], previous[column - 1]
            )
        previous = current
    return previous[columns] / (rows + columns)


def estimate_threshold(samples):
    values = []
    for left in range(len(samples)):
        for right in range(left + 1, len(samples)):
            values.append(distance(samples[left], samples[right]))
    if not values:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return mean + 2.0 * math.sqrt(variance)

