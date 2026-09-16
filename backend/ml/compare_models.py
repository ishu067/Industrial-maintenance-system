from backend.ml.risk import assess


def compare() -> list[dict[str, str | float]]:
    samples = [(42, 1.0, 4.0, 20_000), (65, 3.0, 8.0, 75_000), (88, 5.5, 11.0, 95_000)]
    return [{"model": "weighted-threshold-baseline", "risk": assess(*sample).level, "score": assess(*sample).score} for sample in samples]


if __name__ == "__main__":
    for result in compare():
        print(result)