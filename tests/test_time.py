from datetime import datetime, timedelta, timezone

import pytest

from yumako.time import display, duration, of


def test_display_without_double_digits() -> None:
    # Test various timedelta combinations
    assert display(timedelta(days=365 * 2 + 7 * 3)) == "2y3w"
    assert display(timedelta(days=7 * 2 + 3)) == "2w3d"
    assert display(timedelta(days=2, hours=5)) == "2d5h"
    assert display(timedelta(hours=3, minutes=30)) == "3h30m"
    assert display(timedelta(minutes=5, seconds=30)) == "5m30s"
    assert display(timedelta(seconds=45)) == "45s"


def test_display_with_double_digits() -> None:
    # Test various timedelta combinations with double digits
    assert display(timedelta(days=365 * 2 + 7 * 3), True) == "02y03w"
    assert display(timedelta(days=7 * 2 + 3), True) == "02w03d"
    assert display(timedelta(days=2, hours=5), True) == "02d05h"
    assert display(timedelta(hours=3, minutes=30), True) == "03h30m"
    assert display(timedelta(minutes=5, seconds=30), True) == "05m30s"
    assert display(timedelta(seconds=45), True) == "45s"


def test_of_basic_types() -> None:
    # Test datetime input
    dt = datetime(2023, 12, 4, 12, 30, 45, tzinfo=timezone.utc)
    assert of(dt) == dt

    # Test "now"
    now = datetime.now(timezone.utc)
    result = of("now")
    assert abs((result - now).total_seconds()) < 1  # Within 1 second

    # Test millisecond timestamp
    base_dt = datetime(2023, 12, 4, 12, 0, 0, tzinfo=timezone.utc)
    ts = int(base_dt.timestamp() * 1000)
    result = of(ts)
    expected = base_dt

    # Compare with microsecond precision removed
    assert result.replace(microsecond=0) == expected.replace(microsecond=0)

    # Test timestamp as string
    assert of(str(ts)).replace(microsecond=0) == expected.replace(microsecond=0)

    # Test second-based timestamp
    ts_seconds = int(base_dt.timestamp())
    assert of(str(ts_seconds)).replace(microsecond=0) == expected.replace(microsecond=0)


def test_of_relative_times() -> None:
    now = datetime.now(timezone.utc)

    # Test single units
    assert of("-1h").replace(microsecond=0) == (now - timedelta(hours=1)).replace(microsecond=0)
    assert of("+30m").replace(microsecond=0) == (now + timedelta(minutes=30)).replace(microsecond=0)
    assert of("-7d").replace(microsecond=0) == (now - timedelta(days=7)).replace(microsecond=0)
    assert of("+1w").replace(microsecond=0) == (now + timedelta(weeks=1)).replace(microsecond=0)
    assert of("-45s").replace(microsecond=0) == (now - timedelta(seconds=45)).replace(microsecond=0)

    # Test multiple units
    assert of("-1h30m").replace(microsecond=0) == (now - timedelta(hours=1, minutes=30)).replace(microsecond=0)
    assert of("+1w2d").replace(microsecond=0) == (now + timedelta(weeks=1, days=2)).replace(microsecond=0)
    assert of("-7d12h30m").replace(microsecond=0) == (now - timedelta(days=7, hours=12, minutes=30)).replace(
        microsecond=0
    )


def test_of_iso_formats() -> None:
    # Full ISO format with milliseconds and Z
    a = of("2023-12-04T12:30:45.123Z")
    b = datetime(2023, 12, 4, 12, 30, 45, 123000, tzinfo=timezone.utc)
    print(a, b)
    assert a == b
    assert of("2023-12-04T12:30:45.123Z") == datetime(2023, 12, 4, 12, 30, 45, 123000, tzinfo=timezone.utc)

    # Test case insensitivity
    assert of("2023-12-04t12:30:45.123z") == datetime(2023, 12, 4, 12, 30, 45, 123000, tzinfo=timezone.utc)

    # Basic ISO formats
    assert of("2023-12-04T12:30:45Z") == datetime(2023, 12, 4, 12, 30, 45, 0, tzinfo=timezone.utc)
    assert of("2023-12-04T12:30:45") == datetime(2023, 12, 4, 12, 30, 45, 0, tzinfo=timezone.utc)
    assert of("2023-12-04 12:30:45") == datetime(2023, 12, 4, 12, 30, 45, 0, tzinfo=timezone.utc)

    # ISO format without timezone
    assert of("2023-12-04T12:30:45") == datetime(2023, 12, 4, 12, 30, 45, tzinfo=timezone.utc)

    # Space separator
    assert of("2023-12-04 12:30:45") == datetime(2023, 12, 4, 12, 30, 45, tzinfo=timezone.utc)

    # Time only with Z
    today = datetime.now(timezone.utc).date()
    assert of("12:30:45Z") == datetime.combine(
        today, datetime.strptime("12:30:45", "%H:%M:%S").time(), tzinfo=timezone.utc
    )

    # Date only
    assert of("2023-12-04") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)

    # Time only
    today = datetime.now(timezone.utc).date()
    assert of("12:30") == datetime.combine(today, datetime.strptime("12:30", "%H:%M").time(), tzinfo=timezone.utc)


def test_of_timezone_offsets() -> None:
    # ISO with positive offset
    assert of("2023-12-04T12:30:45+01:00") == datetime(2023, 12, 4, 11, 30, 45, tzinfo=timezone.utc)

    # ISO with negative offset
    assert of("2023-12-04T12:30:45-05:00") == datetime(2023, 12, 4, 17, 30, 45, tzinfo=timezone.utc)
    # ISO with milliseconds and offset
    assert of("2023-12-04T12:30:45.123+01:00") == datetime(2023, 12, 4, 11, 30, 45, 123000, tzinfo=timezone.utc)
    assert of("2023-12-04T12:30:45+0000") == datetime(2023, 12, 4, 12, 30, 45, tzinfo=timezone.utc)
    assert of("2023-12-04T12:30:45.123+00:00") == datetime(2023, 12, 4, 12, 30, 45, 123000, tzinfo=timezone.utc)


def test_of_common_formats() -> None:
    # US date (MM/DD/YYYY)
    assert of("12/04/2023") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)
    assert of("04-12-2023") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)
    assert of("2023.12.04") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)

    # Compact date
    assert of("20231204") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)

    # Forward slash date
    assert of("2023/12/04") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)

    # European dates
    assert of("04.12.2023") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)


def test_of_month_name_formats() -> None:
    # Short month with comma
    assert of("Dec 4, 2023") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)

    # Short month without comma
    assert of("Dec 4 2023") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)

    # Day first
    assert of("4 Dec 2023") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)

    # Full month name
    assert of("December 4, 2023") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)


def test_of_rfc2822() -> None:
    # RFC 2822 format
    assert of("Mon, 04 Dec 2023 12:30:45 +0000") == datetime(2023, 12, 4, 12, 30, 45, tzinfo=timezone.utc)
    assert of("Mon, 04 Dec 2023 12:30:45 -0500") == datetime(2023, 12, 4, 17, 30, 45, tzinfo=timezone.utc)


def test_of_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        of("invalid date")

    with pytest.raises(ValueError):
        of(None)

    with pytest.raises(ValueError):
        of([])

    with pytest.raises(ValueError):
        of("2023-13-45")  # Invalid month/day

    with pytest.raises(ValueError):
        of("25:70")  # Invalid time


def test_duration() -> None:
    # Test basic durations
    assert duration("PT5S") == 5
    assert duration("PT5M") == 5 * 60
    assert duration("PT5H") == 5 * 3600
    assert duration("P1D") == 24 * 3600

    # Test combined durations
    assert duration("PT2H3M4S") == 2 * 3600 + 3 * 60 + 4
    assert duration("P1DT2H") == 24 * 3600 + 2 * 3600

    # Test invalid formats
    with pytest.raises(ValueError):
        duration("invalid")
    with pytest.raises(ValueError):
        duration("PT")


def test_duration_iso_format() -> None:
    # Test ISO-8601 format durations

    # Basic units
    assert duration("PT5S") == 5
    assert duration("PT9M") == timedelta(minutes=9).total_seconds()
    assert duration("PT2H") == timedelta(hours=2).total_seconds()
    assert duration("P1D") == timedelta(days=1).total_seconds()
    assert duration("P1W") == timedelta(weeks=1).total_seconds()

    # Combined units
    assert duration("PT9M15S") == timedelta(minutes=9, seconds=15).total_seconds()
    assert duration("PT2H30M") == timedelta(hours=2, minutes=30).total_seconds()
    assert duration("PT1H30M15S") == timedelta(hours=1, minutes=30, seconds=15).total_seconds()
    assert duration("P1DT2H") == timedelta(days=1, hours=2).total_seconds()
    assert duration("P1W2D") == timedelta(weeks=1, days=2).total_seconds()

    # Complex combinations
    assert duration("P1W2DT3H4M5S") == timedelta(weeks=1, days=2, hours=3, minutes=4, seconds=5).total_seconds()

    # Decimal seconds
    assert duration("PT0.5S") == int(timedelta(seconds=0.5).total_seconds())
    assert duration("PT10.123S") == int(timedelta(seconds=10.123).total_seconds())


def test_duration_human_format() -> None:
    # Test human-readable format durations

    # Basic units
    assert duration("5S") == 5
    assert duration("9M") == 9 * 60
    assert duration("2H") == 2 * 3600
    assert duration("1D") == 24 * 3600
    assert duration("1W") == 7 * 24 * 3600

    # Combined units
    assert duration("1H30M") == 1 * 3600 + 30 * 60
    assert duration("1W2D") == 7 * 24 * 3600 + 2 * 24 * 3600
    assert duration("7D12H") == 7 * 24 * 3600 + 12 * 3600
    assert duration("30M15S") == 30 * 60 + 15

    # Complex combinations
    assert duration("1W2D3H4M5S") == 7 * 24 * 3600 + 2 * 24 * 3600 + 3 * 3600 + 4 * 60 + 5


def test_duration_case_insensitivity() -> None:
    # Test that both upper and lower case work
    assert duration("1h30m") == duration("1H30M")
    assert duration("pt1h30m") == duration("PT1H30M")
    assert duration("1w2d") == duration("1W2D")
    assert duration("p1w2d") == duration("P1W2D")


def test_duration_invalid_formats() -> None:
    # Test invalid formats
    with pytest.raises(ValueError):
        duration("invalid")

    with pytest.raises(ValueError):
        duration("PT")

    with pytest.raises(ValueError):
        duration("P")

    with pytest.raises(ValueError):
        duration("1X")  # Invalid unit

    with pytest.raises(ValueError):
        duration("PT1H2X")  # Invalid unit in combination

    with pytest.raises(ValueError):
        duration("")  # Empty string

    with pytest.raises(ValueError):
        duration("P1YT1H")  # Years not supported

    with pytest.raises(ValueError):
        duration("30M1H")

    with pytest.raises(ValueError):
        duration("3H2D1W")


def test_duration_zero_values() -> None:
    # Test zero values
    assert duration("PT0S") == 0
    assert duration("P0D") == 0
    assert duration("0S") == 0
    assert duration("P0W0DT0H0M0S") == 0
    assert duration("0W0D0H0M0S") == 0


def test_duration_ordering() -> None:
    # But order matters in ISO format
    with pytest.raises(ValueError):
        duration("PT30M1H")  # Invalid ISO format - wrong order


def test_of_edge_cases() -> None:
    # Test whitespace handling
    assert of("  2023-12-04  ") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)
    assert of(" 12:30:45Z ") == datetime.combine(
        datetime.now(timezone.utc).date(),
        datetime.strptime("12:30:45", "%H:%M:%S").time(),
        tzinfo=timezone.utc,
    )

    # Test case sensitivity
    assert of("2023-12-04t12:30:45z") == datetime(2023, 12, 4, 12, 30, 45, tzinfo=timezone.utc)
    assert of("DEC 4, 2023") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)
    assert of("dec 4, 2023") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)


def test_of_relative_time_edge_cases() -> None:
    # Test zero values
    assert of("+0h").replace(second=0, microsecond=0) == of("now").replace(second=0, microsecond=0)
    assert of("-0d").replace(second=0, microsecond=0) == of("now").replace(second=0, microsecond=0)

    # Test decimal values in timestamps
    ts = datetime(2023, 12, 4, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    assert of(str(ts)) == datetime(2023, 12, 4, 12, 0, 0, tzinfo=timezone.utc)
    assert of(str(int(ts))) == datetime(2023, 12, 4, 12, 0, 0, tzinfo=timezone.utc)


def test_of_timezone_variations() -> None:
    # Test various timezone offset formats
    base = datetime(2023, 12, 4, 12, 30, 45, tzinfo=timezone.utc)

    # Compact format without colons
    assert of("2023-12-04T12:30:45+0000") == base
    assert of("2023-12-04T12:30:45-0500") == base.replace(hour=17, minute=30)

    # With milliseconds
    assert of("2023-12-04T12:30:45.123+0000") == base.replace(microsecond=123000)
    assert of("2023-12-04T12:30:45.123-0500") == base.replace(hour=17, minute=30, microsecond=123000)

    # With colons in offset
    assert of("2023-12-04T12:30:45+00:00") == base
    assert of("2023-12-04T12:30:45-05:00") == base.replace(hour=17, minute=30)


def test_of_partial_formats() -> None:
    today = datetime.now(timezone.utc).date()

    # Test time-only formats with various precisions
    assert of("12:30").replace(year=today.year, month=today.month, day=today.day) == datetime.combine(
        today, datetime.strptime("12:30", "%H:%M").time(), tzinfo=timezone.utc
    )

    assert of("12:30:45").replace(year=today.year, month=today.month, day=today.day) == datetime.combine(
        today, datetime.strptime("12:30:45", "%H:%M:%S").time(), tzinfo=timezone.utc
    )

    # Test date-only formats
    assert of("2023-12-04") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)
    assert of("20231204") == datetime(2023, 12, 4, 0, 0, 0, tzinfo=timezone.utc)


def test_of_invalid_formats() -> None:
    invalid_inputs = [
        "2023-13-01",  # Invalid month
        "2023-12-32",  # Invalid day
        "25:00",  # Invalid hour
        "12:60",  # Invalid minute
        "12:30:61",  # Invalid second
        "2023-12-04T25:30:45",  # Invalid hour
        "2023-12-04T12:30:45+15:00",  # Invalid timezone offset
        "1h30m15",  # Incomplete unit specifier
        "next week",  # Unsupported relative format
        "tomorrow",  # Unsupported relative format
        "",  # Empty string
        " ",  # Whitespace only
        "2023-12-04T",  # Incomplete ISO format
        "T12:30:45",  # Missing date in ISO format
        "2023-W01",  # Unsupported week format
        "2023-366",  # Unsupported ordinal date format
    ]

    for invalid_input in invalid_inputs:
        try:
            of(invalid_input)
            pytest.fail(f"Expected ValueError for input: [{invalid_input}]")
        except ValueError as e:
            if "Unsupported time format" in str(e):
                pass  # good
            else:
                print(f"Got different error message for [{invalid_input}]: {str(e)}")
                raise


def test_display_basic() -> None:
    # Test basic timedelta displays
    assert display(timedelta(seconds=30)) == "30s"
    assert display(timedelta(minutes=5)) == "5m"
    assert display(timedelta(hours=2)) == "2h"
    assert display(timedelta(days=3)) == "3d"
    assert display(timedelta(weeks=1)) == "1w"
    assert display(timedelta(days=365)) == "1y"


def test_display_combined() -> None:
    # Test combinations of units
    assert display(timedelta(minutes=5, seconds=30)) == "5m30s"
    assert display(timedelta(hours=2, minutes=15)) == "2h15m"
    assert display(timedelta(days=3, hours=6)) == "3d6h"
    assert display(timedelta(weeks=2, days=3)) == "2w3d"
    assert display(timedelta(days=365 + 14)) == "1y2w"


def test_display_double_digits() -> None:
    # Test with double digit formatting
    assert display(timedelta(seconds=5), use_double_digits=True) == "05s"
    assert display(timedelta(minutes=5, seconds=5), use_double_digits=True) == "05m05s"
    assert display(timedelta(hours=5, minutes=5), use_double_digits=True) == "05h05m"
    assert display(timedelta(days=5, hours=5), use_double_digits=True) == "05d05h"
    assert display(timedelta(weeks=5, days=5), use_double_digits=True) == "05w05d"
    assert display(timedelta(days=365 + 7 * 5), use_double_digits=True) == "01y05w"


def test_display_zero_values() -> None:
    # Test handling of zero values
    assert display(timedelta(0)) == "0s"
    assert display(timedelta(0), use_double_digits=True) == "00s"
    assert display(timedelta(minutes=1, seconds=0)) == "1m"
    assert display(timedelta(hours=1, minutes=0)) == "1h"
    assert display(timedelta(days=1, hours=0)) == "1d"
    assert display(timedelta(weeks=1, days=0)) == "1w"
    assert display(timedelta(days=365, weeks=0)) == "1y"


def test_display_large_values() -> None:
    # Test large time spans
    assert display(timedelta(days=365 * 5 + 7 * 3)) == "5y3w"
    assert display(timedelta(days=7 * 52 + 3)) == "1y2d"
    assert display(timedelta(hours=24 * 7 + 5)) == "1w5h"
    assert display(timedelta(minutes=60 * 5 + 30)) == "5h30m"
    assert display(timedelta(seconds=60 * 5 + 30)) == "5m30s"


def test_display_negative_values() -> None:
    # Test negative timedeltas
    assert display(timedelta(days=-365)) == "-1y"
    assert display(timedelta(days=-7)) == "-1w"
    assert display(timedelta(hours=-24)) == "-1d"
    assert display(timedelta(minutes=-60)) == "-1h"
    assert display(timedelta(seconds=-60)) == "-1m"
    assert display(timedelta(seconds=-30)) == "-30s"


def test_display_edge_cases() -> None:
    # Test edge cases and unusual values
    assert display(timedelta(microseconds=999999)) == "0s"  # Less than 1 second
    assert display(timedelta(days=365 * 10 + 7 * 26)) == "10y26w"  # Large combined value
    assert display(timedelta(days=364)) == "52w"  # Just under a year
    assert display(timedelta(days=366)) == "1y1d"  # Just over a year
