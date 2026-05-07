from tqdm import tqdm


def track(iterable, desc: str = "", total: int | None = None):
    return tqdm(iterable, desc=desc, total=total, unit="card")
