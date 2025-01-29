import re as __re
from datetime import datetime, timedelta, timezone
from typing import Union


def display(d: timedelta, use_double_digits: bool = False) -> str:
    """
    Format a timedelta into a human-readable string.

    Args:
        d: The timedelta to format
        use_double_digits: If True, pad numbers with leading zeros

    Returns:
        A formatted string like "1y2w" or "01y02w" depending on use_double_digits
    """
    is_negative = d.total_seconds() < 0
    if is_negative:
        d = abs(d)

    total_days = d.days

    # Only use years if we have exactly 365 days or more
    years = total_days // 365 if total_days >= 365 else 0
    remaining_days = total_days % 365 if years > 0 else total_days

    weeks = remaining_days // 7
    days = remaining_days % 7

    hours = d.seconds // 3600
    remaining = d.seconds % 3600
    minutes = remaining // 60
    seconds = remaining % 60

    parts = []
    if years > 0:
        parts.append((years, "y"))
    if weeks > 0:
        parts.append((weeks, "w"))
    if days > 0:
        parts.append((days, "d"))
    if hours > 0:
        parts.append((hours, "h"))
    if minutes > 0:
        parts.append((minutes, "m"))
    if seconds > 0:
        parts.append((seconds, "s"))

    if len(parts) > 2:
        parts = parts[:2]
    elif len(parts) == 0:
        return "00s" if use_double_digits else "0s"

    ret = "-" if is_negative else ""
    for part in parts:
        if use_double_digits:
            ret += f"{part[0]:02d}{part[1]}"
        else:
            ret += f"{part[0]}{part[1]}"
    return ret


def _parse_iso_with_colon_offset(x: str) -> datetime:
    if abs(int(x[-5:-3])) > 14:
        raise ValueError("Invalid timezone offset")
    return datetime.strptime(
        f"{x[:-6]}{x[-6:].replace(':','')}",
        "%Y-%m-%dT%H:%M:%S.%f%z" if "." in x else "%Y-%m-%dT%H:%M:%S%z",
    )


def _parse_iso_with_colon_offset2(x: str) -> datetime:
    if abs(int(x[-4:-2])) > 14:
        raise ValueError("Invalid timezone offset")
    return datetime.strptime(x, "%Y-%m-%dT%H:%M:%S.%f%z" if "." in x else "%Y-%m-%dT%H:%M:%S%z")


# Try parsing common formats
_all_human_time_formats = [
    # Unix timestamps
    (r"^\d{13}$", lambda x: datetime.fromtimestamp(int(x) / 1000, tz=timezone.utc)),
    (r"^\d{10}$", lambda x: datetime.fromtimestamp(int(x), tz=timezone.utc)),
    (r"^\d+\.\d+$", lambda x: datetime.fromtimestamp(float(x), tz=timezone.utc)),
    # ISO formats
    (r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", "%Y-%m-%dT%H:%M:%S.%fZ"),
    (r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", "%Y-%m-%dT%H:%M:%SZ"),
    (r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", "%Y-%m-%dT%H:%M:%S"),
    (r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", "%Y-%m-%d %H:%M:%S"),
    (
        r"^\d{2}:\d{2}:\d{2}Z$",
        lambda x: datetime.combine(
            datetime.now(timezone.utc).date(),
            datetime.strptime(x, "%H:%M:%SZ").time(),
            tzinfo=timezone.utc,
        ),
    ),
    (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),
    (
        r"^\d{2}:\d{2}$",
        lambda x: datetime.combine(
            datetime.now(timezone.utc).date(),
            datetime.strptime(x, "%H:%M").time(),
            tzinfo=timezone.utc,
        ),
    ),
    # Non-standard formats
    (r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+$", "%Y-%m-%d %H:%M:%S.%f"),
    (r"^\d{2}/\d{2}/\d{4}$", "%m/%d/%Y"),
    (r"^\d{4}\.\d{2}\.\d{2}$", "%Y.%m.%d"),
    (r"^\d{8}$", "%Y%m%d"),
    (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d"),
    # RFC 2822
    (
        r"^[A-Z]{3}, \d{2} [A-Z]{3} \d{4} \d{2}:\d{2}:\d{2} [+-]\d{4}$",
        "%a, %d %b %Y %H:%M:%S %z",
    ),
    # ISO with timezone offset (with colon)
    (
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2}$",
        _parse_iso_with_colon_offset,
    ),
    # ISO with timezone offset (without colon)
    (
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{4}$",
        _parse_iso_with_colon_offset2,
    ),
    # European date formats
    (r"^\d{2}-\d{2}-\d{4}$", ["%d-%m-%Y", "%m-%d-%Y"]),
    (r"^\d{2}/\d{2}/\d{4}$", ["%d/%m/%Y", "%m/%d/%Y"]),
    (r"^\d{2}\.\d{2}\.\d{4}$", ["%d.%m.%Y", "%m.%d.%Y"]),
    # Additional common formats
    (r"^[A-Z]{3} \d{1,2}, \d{4}$", "%b %d, %Y"),  # DEC 4, 2023
    (r"^[A-Z]{3} \d{1,2} \d{4}$", "%b %d %Y"),  # DEC 4 2023
    (r"^\d{1,2} [A-Z]{3} \d{4}$", "%d %b %Y"),  # 4 DEC 2023
    (r"^[A-Z]{6,9} \d{1,2}, \d{4}$", "%B %d, %Y"),  # DECEMBER 4, 2023
    # Time only with Z
    (
        r"^\d{2}:\d{2}:\d{2}Z$",
        lambda x: datetime.combine(
            datetime.now(timezone.utc).date(),
            datetime.strptime(x, "%H:%M:%SZ").time(),
            tzinfo=timezone.utc,
        ),
    ),
    # Time only without Z
    (
        r"^\d{2}:\d{2}:\d{2}$",
        lambda x: datetime.combine(
            datetime.now(timezone.utc).date(),
            datetime.strptime(x, "%H:%M:%S").time(),
            tzinfo=timezone.utc,
        ),
    ),
    # Time only (HH:MM)
    (
        r"^\d{2}:\d{2}$",
        lambda x: datetime.combine(
            datetime.now(timezone.utc).date(),
            datetime.strptime(x, "%H:%M").time(),
            tzinfo=timezone.utc,
        ),
    ),
]

# Could cache compiled regex patterns
_COMPILED_PATTERNS = [(__re.compile(pattern), handler) for pattern, handler in _all_human_time_formats]


def of(human_time: Union[str, datetime, int, float]) -> datetime:
    """
    Convert various time formats (ISO-8601, Unix timestamps, relative times, etc.) to a datetime object.

    Args:
        human_time: Input time in one of these formats:
            - int: Unix timestamp in milliseconds
            - datetime: Returns the input unchanged
            - str: One of:
                - "now": Current UTC time
                - Relative time with +/- (e.g. "-1h", "-7d","+30m", "+1w")
                - Relative time with multiple units (e.g. "-1h30m", "+1w2d", "-7d12h30m")
                - Unix timestamp in milliseconds as string (e.g. "1734010792148") or seconds (e.g. "1734010792")
                - ISO formats:
                    - With milliseconds and Z (e.g. "2023-12-04T00:19:22.854Z")
                    - With Z (e.g. "2023-12-04T00:19:22Z")
                    - Without timezone (e.g. "2023-12-04T00:19:22")
                    - With space separator (e.g. "2023-12-04 00:19:22")
                    - Time only with Z (e.g. "00:19:22Z")
                    - Date only (e.g. "2023-12-04")
                    - Time only (e.g. "00:19")
                    - With timezone offset (e.g. "2023-12-04T00:19:22+01:00", "2023-12-04T00:19:22-0500")
                        Valid offsets are between -14:00 and +14:00
                - Common formats:
                    - With milliseconds (e.g. "2023-12-04 00:19:22.854")
                    - US date (e.g. "12/04/2023")
                    - Dotted date (e.g. "2023.12.04")
                    - Compact date (e.g. "20231204")
                    - Forward slash date (e.g. "2023/12/04")
                    - RFC 2822 (e.g. "Mon, 04 Dec 2023 00:19:22 +0000")
                    - European dates (e.g. "04-12-2023", "04/12/2023", "04.12.2023")
                    - Month name formats:
                        - Short with comma (e.g. "Dec 4, 2023")
                        - Short without comma (e.g. "Dec 4 2023")
                        - Day first (e.g. "4 Dec 2023")
                        - Full month (e.g. "December 4, 2023")

    Returns:
        datetime: A timezone-aware datetime object

    Raises:
        ValueError: If the input format is not recognized or invalid (e.g., timezone offset > ±14:00)

    Examples:
        >>> of("-1d")
        minus 1 day from now
        >>> of("+2w")
        plus 2 weeks from now
        >>> of("2023-12-04T12:30:45+02:00")
        Parsing common time formats
    """
    if isinstance(human_time, int):
        return datetime.fromtimestamp(human_time / 1000, tz=timezone.utc)

    if isinstance(human_time, float):
        return datetime.fromtimestamp(human_time / 1000, tz=timezone.utc)

    if isinstance(human_time, datetime):
        return human_time.astimezone(timezone.utc)

    if not isinstance(human_time, str):
        raise ValueError("Invalid input type: " + type(human_time).__name__)

    human_time = human_time.strip()
    original_input = human_time  # Keep original for error message
    human_time = human_time.upper()  # Convert to uppercase for simpler regex matching

    if human_time == "NOW":
        return datetime.now(timezone.utc)

    # Handle relative times (+/-)
    if human_time.startswith("-") or human_time.startswith("+"):
        sign = -1 if human_time.startswith("-") else 1

        # Remove leading +/- and split into components
        time_str = human_time[1:]
        time_delta = timedelta(seconds=duration(time_str))
        return datetime.now(timezone.utc) + time_delta * sign

    # Try each format pattern
    for pattern, fmt in _COMPILED_PATTERNS:
        if __re.match(pattern, human_time):
            try:
                if callable(fmt):
                    dt: datetime = fmt(human_time)
                    if not isinstance(dt, datetime):
                        raise ValueError(f"Expected datetime, got {type(dt).__name__}")
                    return dt
                if isinstance(fmt, list):
                    # Try multiple formats
                    for f in fmt:
                        try:
                            dt = datetime.strptime(human_time, f)
                            if dt.tzinfo is None:
                                return dt.replace(tzinfo=timezone.utc)  # Treat naive times as UTC
                            else:
                                return dt.astimezone(timezone.utc)
                        except ValueError:
                            continue
                dt = datetime.strptime(human_time, str(fmt))
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                else:
                    return dt.astimezone(timezone.utc)
            except ValueError:
                continue

    raise ValueError("Unsupported time format: " + original_input)


def duration(human_time: str) -> int:
    """
    Parse a human-friendly duration string into seconds, either ISO-8601 format or human format.
    Less than 1 second is rounded to 0.

    Args:
        human_time (str): Duration string in:
            ISO-8601 format (e.g. 'PT5M', 'P1DT2H'),
            human format (e.g. '1h30m', '1w2d', '7d12h30m')

    Returns:
        timedelta: The parsed duration as a timedelta object

    Raises:
        ValueError: If the duration string format is not supported

    Examples:
        >>> duration('PT5S')  # 5 seconds
        >>> duration('PT9M15S')  # 9 minutes 15 seconds
        >>> duration('PT9H15M')  # 9 hours 15 minutes
        >>> duration('P1DT2H')  # 1 day 2 hours
        >>> duration('30m')  # 30 minutes
        >>> duration('1h30m')  # 1 hour 30 minutes
        >>> duration('1w2d')  # 1 week 2 days
        >>> duration('7d12h30m')  # 7 days 12 hours 30 minutes
    """

    if not human_time:
        raise ValueError(f"Invalid duration format: {human_time}")

    human_time = human_time.upper()

    # First try ISO-8601 format
    iso_pattern = r"^P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$"
    iso_match = __re.match(iso_pattern, human_time)

    if iso_match:
        # PT with no values specified is invalid - must have at least one value
        if human_time == "PT" or human_time == "P" or human_time == "":
            raise ValueError(f"Invalid duration format: {human_time}")

        weeks = int(iso_match.group(1) or 0)
        days = int(iso_match.group(2) or 0)
        hours = int(iso_match.group(3) or 0)
        minutes = int(iso_match.group(4) or 0)
        seconds = float(iso_match.group(5) or 0)

        return int(timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds).total_seconds())

    # Try human readable format (e.g. 1h30m, 1w2d)
    human_pattern = r"^(?:(\d+)Y)?(?:(\d+)W)?(?:(\d+)D)?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$"
    human_match = __re.match(human_pattern, human_time)

    if human_match:
        years = int(human_match.group(1) or 0)
        weeks = int(human_match.group(2) or 0)
        days = int(human_match.group(3) or 0)
        hours = int(human_match.group(4) or 0)
        minutes = int(human_match.group(5) or 0)
        seconds = int(human_match.group(6) or 0)

        # Convert years to days (assuming 365 days per year)
        days_from_years = years * 365

        return int(
            timedelta(
                weeks=weeks,
                days=days + days_from_years,
                hours=hours,
                minutes=minutes,
                seconds=seconds,
            ).total_seconds()
        )

    raise ValueError(f"Unsupported duration format: {human_time}")
