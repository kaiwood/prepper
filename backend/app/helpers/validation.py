class InputLengthError(ValueError):
    def __init__(self, *, field: str, max_length: int, actual_length: int):
        super().__init__(f"{field} exceeds maximum length of {max_length} characters")
        self.field = field
        self.max_length = max_length
        self.actual_length = actual_length


def validate_string_length(value: str, *, field: str, max_length: int) -> None:
    if len(value) > max_length:
        raise InputLengthError(
            field=field,
            max_length=max_length,
            actual_length=len(value),
        )


def input_length_error_payload(error: InputLengthError) -> dict[str, int | str]:
    return {
        "error": "input_too_long",
        "field": error.field,
        "max_length": error.max_length,
        "actual_length": error.actual_length,
    }
