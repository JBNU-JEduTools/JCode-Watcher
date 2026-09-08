import re


_ASSIGNMENT_KEY = re.compile(r"^assignment-(\d+)$")


def assignment_id_from_hw_name(hw_name: str) -> int | None:
    """Return the immutable assignment id encoded by a V2 workspace key."""
    match = _ASSIGNMENT_KEY.fullmatch(hw_name)
    return int(match.group(1)) if match else None


def assignment_predicates(model, class_div: str, hw_name: str):
    assignment_id = assignment_id_from_hw_name(hw_name)
    if assignment_id is not None:
        return (model.assignment_id == assignment_id,)
    return (model.class_div == class_div, model.hw_name == hw_name)
