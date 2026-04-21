from dataclasses import dataclass


@dataclass(frozen=True)
class Batch:
    batch_id: str
    files: tuple[str, ...]


def plan_batches(files: list[str], batch_size: int) -> list[Batch]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    batches: list[Batch] = []
    for i in range(0, len(files), batch_size):
        chunk = tuple(files[i : i + batch_size])
        batches.append(Batch(batch_id=f"b{len(batches):03d}", files=chunk))
    return batches
