from flask import request


def field(name, label, maximum, *, optional=False):
    value = request.form.get(name, "").strip()
    if (not value and not optional) or len(value) > maximum:
        raise ValueError(f"{label} must be {'at most' if optional else 'between 1 and'} {maximum} characters.")
    return value


def number(name, label, maximum, *, optional=False):
    value = request.form.get(name, "").strip()
    if not value and optional:
        return None
    if not value.isascii() or not value.isdecimal() or len(value) > 4 or int(value) > maximum:
        raise ValueError(f"{label} must be a whole number from 0 to {maximum}.")
    return int(value)
