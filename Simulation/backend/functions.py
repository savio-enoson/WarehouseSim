import numpy as np


def bimodal_distribution(x, bottom, peaks=None, weights=None, std_dev=2):
    if not peaks or not weights:  # Return uniform distribution when no peaks are specified
        return np.full_like(x, (1 - bottom) / len(x)) + bottom

    y = np.zeros_like(x)

    for peak, weight in zip(peaks, weights):
        gaussian = weight * np.exp(-0.5 * ((x - peak) / std_dev) ** 2)
        y += gaussian

    y_min = np.min(y)
    y_max = np.max(y)
    y_normal = bottom + ((y - y_min) / (y_max - y_min)) * (1 - bottom)

    return y_normal


def get_class(names, probs, input, time_range=None):
    sum_prob = [sum(probs[:i + 1]) for i in range(len(probs))]

    class_value = None
    for i, cp in enumerate(sum_prob):
        if input <= cp:
            class_value = names[i]
            break

    return class_value


def map_size(size, load):
    vol_map = {'S': 3000, 'M': 5000, 'L': 9000, 'XL': 16000}
    weight_map = {'S': 1500, 'M': 2500, 'L': 4500, 'XL': 8000}
    return vol_map[size] * load, weight_map[size] * load
