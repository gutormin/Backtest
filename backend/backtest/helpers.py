import math

_WEIGHTS_CACHE = {}

def weighted_mean(values, decay=0.06):
    if not values:
        return 0.0
    n = len(values)
    cache_key = (n, decay)
    global _WEIGHTS_CACHE
    if cache_key not in _WEIGHTS_CACHE:
        weights = [math.exp(-decay * (n - 1 - i)) for i in range(n)]
        sum_weights = sum(weights)
        _WEIGHTS_CACHE[cache_key] = (weights, sum_weights)
    else:
        weights, sum_weights = _WEIGHTS_CACHE[cache_key]
    return sum(v * w for v, w in zip(values, weights)) / sum_weights

def solve_kelly_multi(probs, outcomes, max_f=1.0):
    low = 0.0
    high = max_f
    ev = sum(p * x for p, x in zip(probs, outcomes))
    if ev <= 0:
        return 0.0
    for _ in range(15):
        mid = (low + high) / 2.0
        deriv = sum(p * x / (1.0 + mid * x) for p, x in zip(probs, outcomes))
        if deriv > 0:
            low = mid
        else:
            high = mid
    return low
