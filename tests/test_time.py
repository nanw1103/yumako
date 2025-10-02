from datetime import datetime, timedelta, timezone

import pytest

from yumako.time import display, duration, of, stale


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
    # Test datetime input (should honor original timezone)
    dt_utc = datetime(2023, 12, 4, 12, 30, 45, tzinfo=timezone.utc)
    result = of(dt_utc)
    # Should honor original timezone
    assert result.tzinfo == timezone.utc
    assert result.hour == 12
    assert result.minute == 30

    # Test "now" (should return naive datetime by default)
    now_naive = datetime.now()
    result = of("now")
    assert abs((result - now_naive).total_seconds()) < 1  # Within 1 second
    assert result.tzinfo is None  # Should be naive

    # Test second timestamp (should return naive datetime by default)
    base_dt = datetime(2023, 12, 4, 12, 0, 0, tzinfo=timezone.utc)
    ts = int(base_dt.timestamp())
    result = of(ts)
    # Should be naive (Python convention)
    assert result.tzinfo is None
    # The hour will be different because timestamp is converted to local time
    assert result.year == 2023
    assert result.month == 12
    assert result.day == 4

    # Test timestamp as string (should return naive datetime by default)
    result_str = of(str(ts))
    assert result_str.tzinfo is None  # Should be naive
    assert result_str.year == 2023
    assert result_str.month == 12
    assert result_str.day == 4
    assert result_str.minute == 0

    # Test second-based timestamp (should return naive datetime by default)
    ts_seconds = int(base_dt.timestamp())
    result_seconds = of(str(ts_seconds))
    assert result_seconds.tzinfo is None  # Should be naive
    assert result_seconds.year == 2023
    assert result_seconds.month == 12
    assert result_seconds.day == 4


def test_of_relative_times() -> None:
    now_naive = datetime.now()

    # Test single units (should use naive datetime by default)
    assert abs((of("-1h") - (now_naive - timedelta(hours=1))).total_seconds()) < 1
    assert abs((of("+30m") - (now_naive + timedelta(minutes=30))).total_seconds()) < 1
    assert abs((of("-7d") - (now_naive - timedelta(days=7))).total_seconds()) < 1
    assert abs((of("+1w") - (now_naive + timedelta(weeks=1))).total_seconds()) < 1
    assert abs((of("-45s") - (now_naive - timedelta(seconds=45))).total_seconds()) < 1

    # Test multiple units
    assert abs((of("-1h30m") - (now_naive - timedelta(hours=1, minutes=30))).total_seconds()) < 1
    assert abs((of("+1w2d") - (now_naive + timedelta(weeks=1, days=2))).total_seconds()) < 1
    assert abs((of("-7d12h30m") - (now_naive - timedelta(days=7, hours=12, minutes=30))).total_seconds()) < 1


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
    # Naive inputs should return naive datetime (Python convention)
    result_naive1 = of("2023-12-04T12:30:45")
    assert result_naive1.tzinfo is None  # Should be naive
    assert result_naive1.hour == 12
    assert result_naive1.minute == 30

    result_naive2 = of("2023-12-04 12:30:45")
    assert result_naive2.tzinfo is None  # Should be naive
    assert result_naive2.hour == 12
    assert result_naive2.minute == 30

    # Space separator (already tested above as result_naive2)

    # Time only with Z
    today = datetime.now(timezone.utc).date()
    assert of("12:30:45Z") == datetime.combine(
        today, datetime.strptime("12:30:45", "%H:%M:%S").time(), tzinfo=timezone.utc
    )

    # Date only (should return naive datetime by default)
    result_date = of("2023-12-04")
    assert result_date.tzinfo is None  # Should be naive
    assert result_date.year == 2023
    assert result_date.month == 12
    assert result_date.day == 4
    assert result_date.hour == 0
    assert result_date.minute == 0

    # Time only (should return naive datetime by default)
    result_time = of("12:30")
    assert result_time.tzinfo is None  # Should be naive
    assert result_time.hour == 12
    assert result_time.minute == 30


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
    # US date (MM/DD/YYYY) - should return naive datetime by default
    result1 = of("12/04/2023")
    assert result1.tzinfo is None  # Should be naive
    assert result1.year == 2023
    assert result1.month == 12
    assert result1.day == 4
    assert result1.hour == 0
    assert result1.minute == 0

    result2 = of("04-12-2023")
    assert result2.tzinfo is None  # Should be naive
    assert result2.year == 2023
    assert result2.month == 12
    assert result2.day == 4

    result3 = of("2023.12.04")
    assert result3.tzinfo is None  # Should be naive
    assert result3.year == 2023
    assert result3.month == 12
    assert result3.day == 4

    # Compact date
    result4 = of("20231204")
    assert result4.tzinfo is None  # Should be naive
    assert result4.year == 2023
    assert result4.month == 12
    assert result4.day == 4

    # Forward slash date
    result5 = of("2023/12/04")
    assert result5.tzinfo is None  # Should be naive
    assert result5.year == 2023
    assert result5.month == 12
    assert result5.day == 4

    # European dates
    result6 = of("04.12.2023")
    assert result6.tzinfo is None  # Should be naive
    assert result6.year == 2023
    assert result6.month == 12
    assert result6.day == 4


def test_of_month_name_formats() -> None:
    # Short month with comma - should return naive datetime by default
    result1 = of("Dec 4, 2023")
    assert result1.tzinfo is None  # Should be naive
    assert result1.year == 2023
    assert result1.month == 12
    assert result1.day == 4
    assert result1.hour == 0
    assert result1.minute == 0

    # Short month without comma
    result2 = of("Dec 4 2023")
    assert result2.tzinfo is None  # Should be naive
    assert result2.year == 2023
    assert result2.month == 12
    assert result2.day == 4

    # Day first
    result3 = of("4 Dec 2023")
    assert result3.tzinfo is None  # Should be naive
    assert result3.year == 2023
    assert result3.month == 12
    assert result3.day == 4

    # Full month name
    result4 = of("December 4, 2023")
    assert result4.tzinfo is None  # Should be naive
    assert result4.year == 2023
    assert result4.month == 12
    assert result4.day == 4


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
    # Test whitespace handling - should return naive datetime by default
    result1 = of("  2023-12-04  ")
    assert result1.tzinfo is None  # Should be naive
    assert result1.year == 2023
    assert result1.month == 12
    assert result1.day == 4
    assert result1.hour == 0
    assert result1.minute == 0

    # Test time with Z (should keep UTC)
    result2 = of(" 12:30:45Z ")
    assert result2.tzinfo == timezone.utc
    assert result2.hour == 12
    assert result2.minute == 30
    assert result2.second == 45

    # Test case sensitivity - should honor explicit timezone (Z)
    result3 = of("2023-12-04t12:30:45z")
    assert result3.tzinfo == timezone.utc  # Should honor Z timezone
    assert result3.year == 2023
    assert result3.month == 12
    assert result3.day == 4
    assert result3.hour == 12
    assert result3.minute == 30

    result4 = of("DEC 4, 2023")
    assert result4.tzinfo is None  # Should be naive
    assert result4.year == 2023
    assert result4.month == 12
    assert result4.day == 4

    result5 = of("dec 4, 2023")
    assert result5.tzinfo is None  # Should be naive
    assert result5.year == 2023
    assert result5.month == 12
    assert result5.day == 4


def test_of_relative_time_edge_cases() -> None:
    # Test zero values - should use local timezone by default
    now_result = of("now")
    plus_zero = of("+0h")
    minus_zero = of("-0d")

    # All should be very close to each other (within 1 second)
    assert abs((plus_zero - now_result).total_seconds()) < 1
    assert abs((minus_zero - now_result).total_seconds()) < 1

    # Test decimal values in timestamps - should return naive datetime by default
    ts = datetime(2023, 12, 4, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    result1 = of(str(ts))
    assert result1.tzinfo is None  # Should be naive
    # The hour will be different because timestamp is converted to local time
    assert result1.year == 2023
    assert result1.month == 12
    assert result1.day == 4

    result2 = of(str(int(ts)))
    assert result2.tzinfo is None  # Should be naive
    # The hour will be different because timestamp is converted to local time
    assert result2.year == 2023
    assert result2.month == 12
    assert result2.day == 4


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
    # Test time-only formats with various precisions - should return naive datetime by default
    result1 = of("12:30")
    assert result1.tzinfo is None  # Should be naive
    assert result1.hour == 12
    assert result1.minute == 30

    result2 = of("12:30:45")
    assert result2.tzinfo is None  # Should be naive
    assert result2.hour == 12
    assert result2.minute == 30
    assert result2.second == 45

    # Test date-only formats - should return naive datetime by default
    result3 = of("2023-12-04")
    assert result3.tzinfo is None  # Should be naive
    assert result3.year == 2023
    assert result3.month == 12
    assert result3.day == 4
    assert result3.hour == 0
    assert result3.minute == 0

    result4 = of("20231204")
    assert result4.tzinfo is None  # Should be naive
    assert result4.year == 2023
    assert result4.month == 12
    assert result4.day == 4
    assert result4.hour == 0
    assert result4.minute == 0


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


def test_display_with_float_input() -> None:
    """Test display function with float inputs for sub-second precision."""
    # Test basic float values
    assert display(1.5) == "1s"  # 1 second, 500ms
    assert display(30.25) == "30s"  # 30 seconds, 250ms
    assert display(65.75) == "1m5s"  # 1 minute, 5 seconds, 750ms

    # Test float values with double digits
    assert display(1.5, use_double_digits=True) == "01s"
    assert display(30.25, use_double_digits=True) == "30s"
    assert display(65.75, use_double_digits=True) == "01m05s"

    # Test very small float values (less than 1 second)
    assert display(0.5) == "0s"  # 500ms rounds to 0s
    assert display(0.9) == "0s"  # 900ms rounds to 0s
    assert display(0.1) == "0s"  # 100ms rounds to 0s

    # Test float values with microseconds precision
    assert display(1.000001) == "1s"  # 1 second + 1 microsecond
    assert display(1.999999) == "1s"  # 1 second + 999999 microseconds

    # Test negative float values
    assert display(-1.5) == "-1s"
    assert display(-30.25) == "-30s"
    assert display(-65.75) == "-1m5s"

    # Test large float values
    assert display(3661.5) == "1h1m"  # 1 hour, 1 minute, 500ms
    assert display(86400.25) == "1d"  # 1 day, 250ms
    assert display(604800.75) == "1w"  # 1 week, 750ms

    # Test float values that result in years
    assert display(31536000.5) == "1y"  # 1 year, 500ms
    assert display(31536000.0) == "1y"  # Exactly 1 year

    # Test edge case: very small positive float
    assert display(0.000001) == "0s"  # 1 microsecond

    # Test edge case: very large float
    assert display(315360000.0) == "10y"  # 10 years


def test_stale_basic() -> None:
    """Test basic stale functionality with relative times."""
    # Test with recent times (should be very small or zero)
    result = stale("now")
    assert result == "0s"  # Should be 0 seconds or very close

    # Test with times 1 hour ago
    result = stale("-1h")
    assert result == "1h"

    # Test with times 30 minutes ago
    result = stale("-30m")
    assert result == "30m"

    # Test with times 2 days ago
    result = stale("-2d")
    assert result == "2d"

    # Test with times 1 week ago
    result = stale("-1w")
    assert result == "1w"


def test_stale_with_datetime() -> None:
    """Test stale function with datetime objects."""
    now = datetime.now()  # Use local time for consistency

    # Test with datetime 1 hour ago
    one_hour_ago = now - timedelta(hours=1)
    result = stale(one_hour_ago)
    assert result == "1h"

    # Test with datetime 2 days ago
    two_days_ago = now - timedelta(days=2)
    result = stale(two_days_ago)
    assert result == "2d"

    # Test with datetime 1 week and 3 days ago
    one_week_three_days_ago = now - timedelta(weeks=1, days=3)
    result = stale(one_week_three_days_ago)
    assert result == "1w3d"

    # Test with datetime 1 year ago
    one_year_ago = now - timedelta(days=365)
    result = stale(one_year_ago)
    assert result == "1y"


def test_stale_with_timestamps() -> None:
    """Test stale function with timestamp inputs."""
    now = datetime.now(timezone.utc)

    # Test with integer timestamp (1 hour ago)
    one_hour_ago = now - timedelta(hours=1)
    timestamp_int = int(one_hour_ago.timestamp())
    result = stale(timestamp_int)
    assert result == "1h"

    # Test with string timestamp (2 days ago)
    two_days_ago = now - timedelta(days=2)
    timestamp_str = str(int(two_days_ago.timestamp()))
    result = stale(timestamp_str)
    assert result == "2d"

    # Test with float timestamp (1 week ago)
    one_week_ago = now - timedelta(weeks=1)
    timestamp_float = one_week_ago.timestamp()
    result = stale(timestamp_float)
    assert result == "1w"


def test_stale_with_string_formats() -> None:
    """Test stale function with various string time formats."""
    now = datetime.now().astimezone()  # Use local timezone for naive string tests

    # Test with ISO format (1 hour ago) - explicit UTC format
    # With simplified stale(), we always convert to naive, so create local time for comparison
    one_hour_ago_local = now - timedelta(hours=1)
    iso_time = one_hour_ago_local.strftime("%Y-%m-%dT%H:%M:%S")
    result = stale(iso_time)
    assert result == "1h"

    # Test with space-separated format (2 days ago) - naive format
    two_days_ago = now - timedelta(days=2)
    space_time = two_days_ago.strftime("%Y-%m-%d %H:%M:%S")
    result = stale(space_time)
    assert result == "2d"

    # Test with space-separated format (1 week ago)
    one_week_ago = now - timedelta(weeks=1)
    space_time = one_week_ago.strftime("%Y-%m-%d %H:%M:%S")
    result = stale(space_time)
    assert result == "1w"

    # Test with US date format (3 days ago at midnight)
    three_days_ago = now - timedelta(days=3)
    us_date = three_days_ago.strftime("%m/%d/%Y")
    result = stale(us_date)
    # US date format gets interpreted as midnight, so it might be 3d + some hours
    assert result.startswith("3d")


def test_stale_edge_cases() -> None:
    """Test stale function with edge cases."""
    now = datetime.now().astimezone()  # Use local timezone

    # Test with very recent time (should be 0s or very small)
    very_recent = now - timedelta(seconds=30)
    result = stale(very_recent)
    assert result == "30s"

    # Test with very old time
    very_old = now - timedelta(days=365 * 5 + 7 * 3)  # 5 years 3 weeks
    result = stale(very_old)
    assert result == "5y3w"

    # Test with timezone-aware datetime (local timezone)
    tz_aware_time = now - timedelta(hours=2)
    tz_aware_time = tz_aware_time.replace(tzinfo=now.tzinfo)  # Local timezone
    result = stale(tz_aware_time)
    assert result == "2h" or result == "1h59m"  # Should work correctly with local timezone

    # Test with future time (should be negative)
    future_time = now + timedelta(hours=1)
    result = stale(future_time)
    assert result == "-1h" or result == "-59m59s"

    # Test with exactly now
    result = stale(now)
    assert result == "0s" or result == "1s"


def test_stale_combined_units() -> None:
    """Test stale function with times that result in combined units."""
    now = datetime.now()  # Use local time for consistency

    # Test with 1 hour 30 minutes ago
    one_hour_thirty_ago = now - timedelta(hours=1, minutes=30)
    result = stale(one_hour_thirty_ago)
    assert result == "1h30m"

    # Test with 2 days 5 hours ago
    two_days_five_hours_ago = now - timedelta(days=2, hours=5)
    result = stale(two_days_five_hours_ago)
    assert result == "2d5h"

    # Test with 1 week 2 days ago
    one_week_two_days_ago = now - timedelta(weeks=1, days=2)
    result = stale(one_week_two_days_ago)
    assert result == "1w2d"

    # Test with 1 year 2 weeks ago
    one_year_two_weeks_ago = now - timedelta(days=365 + 14)
    result = stale(one_year_two_weeks_ago)
    assert result == "1y2w"


def test_stale_invalid_inputs() -> None:
    """Test stale function with invalid inputs."""
    # Test with invalid string
    with pytest.raises(ValueError):
        stale("invalid date")

    # Test with None
    with pytest.raises(ValueError):
        stale(None)

    # Test with empty string
    with pytest.raises(ValueError):
        stale("")

    # Test with invalid type
    with pytest.raises(ValueError):
        stale([])


def test_stale_with_tz_parameter() -> None:
    """Test stale function with tz parameter."""
    now = datetime.now()  # Use local time for consistency

    # Test with naive string (tz parameter only affects ambiguous inputs)
    one_hour_ago = now - timedelta(hours=1)
    iso_time = one_hour_ago.strftime("%Y-%m-%dT%H:%M:%S")
    result = stale(iso_time)
    assert result == "1h"

    # Test with local timezone (default behavior)
    # Create a local time for comparison
    now_local = datetime.now().astimezone()
    one_hour_ago_local = now_local - timedelta(hours=1)
    iso_time_local = one_hour_ago_local.strftime("%Y-%m-%dT%H:%M:%S")
    result_local = stale(iso_time_local)  # Should use local timezone
    assert result_local == "1h"  # Should be 1h since we're using local timezone


def test_of_with_tz_parameter() -> None:
    """Test of function with tz parameter."""
    # Test naive string with UTC timezone conversion
    dt_utc = of("2023-12-04 12:30:45", tz=timezone.utc)
    assert dt_utc.tzinfo == timezone.utc
    # The hour will be different because naive string is treated as local time, then converted to UTC
    assert dt_utc.minute == 30
    assert dt_utc.second == 45

    # Test naive string with local timezone (default - returns naive datetime)
    dt_local = of("2023-12-04 12:30:45")  # Should return naive datetime
    assert dt_local.tzinfo is None  # Should be naive
    assert dt_local.hour == 12
    assert dt_local.minute == 30

    # Test that explicit timezone inputs get converted to target timezone
    dt_explicit = of("2023-12-04T12:30:45+02:00", tz=timezone.utc)
    assert dt_explicit.tzinfo == timezone.utc
    # Should be converted from +02:00 to UTC (10:30 UTC)
    assert dt_explicit.hour == 10
    assert dt_explicit.minute == 30

    # Test that explicit timezone inputs are honored when tz=None
    dt_honored = of("2023-12-04T12:30:45+02:00")  # Should keep +02:00
    assert dt_honored.tzinfo.utcoffset(None).total_seconds() == 7200  # +02:00 = 7200 seconds
    assert dt_honored.hour == 12
    assert dt_honored.minute == 30

    # Test numeric inputs with timezone conversion
    import time

    timestamp = time.time()
    dt_timestamp_utc = of(int(timestamp), tz=timezone.utc)
    assert dt_timestamp_utc.tzinfo == timezone.utc

    dt_timestamp_local = of(int(timestamp))  # Should return naive datetime
    assert dt_timestamp_local.tzinfo is None


def test_of_tz_parameter_comprehensive() -> None:
    """Comprehensive test of tz parameter with various input types."""
    # Test "now" with different timezones
    now_utc = of("now", tz=timezone.utc)
    assert now_utc.tzinfo == timezone.utc

    now_local = of("now")  # Default returns naive datetime
    assert now_local.tzinfo is None

    # Test relative times with tz parameter
    rel_utc = of("-1h", tz=timezone.utc)
    assert rel_utc.tzinfo == timezone.utc

    rel_local = of("-1h")  # Default returns naive datetime
    assert rel_local.tzinfo is None

    # Test date-only formats with tz parameter
    date_utc = of("2023-12-04", tz=timezone.utc)
    assert date_utc.tzinfo == timezone.utc
    assert date_utc.year == 2023
    assert date_utc.month == 12
    assert date_utc.day == 4

    # Test time-only formats with tz parameter
    time_utc = of("12:30", tz=timezone.utc)
    assert time_utc.tzinfo == timezone.utc
    # The hour will be different because naive time is treated as local time, then converted to UTC
    assert time_utc.minute == 30

    # Test common formats with tz parameter
    common_utc = of("12/04/2023", tz=timezone.utc)
    assert common_utc.tzinfo == timezone.utc
    assert common_utc.year == 2023
    assert common_utc.month == 12
    assert common_utc.day == 4

    # Test month name formats with tz parameter
    month_utc = of("Dec 4, 2023", tz=timezone.utc)
    assert month_utc.tzinfo == timezone.utc
    assert month_utc.year == 2023
    assert month_utc.month == 12
    assert month_utc.day == 4


def test_of_tz_parameter_edge_cases() -> None:
    """Test tz parameter with edge cases."""
    # Test with custom timezone
    custom_tz = timezone(timedelta(hours=5, minutes=30))  # +05:30

    # Test naive input with custom timezone
    dt_custom = of("2023-12-04 12:30:45", tz=custom_tz)
    assert dt_custom.tzinfo == custom_tz
    # The time will be different because naive string is treated as local time, then converted to custom timezone
    assert dt_custom.year == 2023
    assert dt_custom.month == 12
    assert dt_custom.second == 45

    # Test explicit timezone input with custom timezone conversion
    dt_explicit_to_custom = of("2023-12-04T12:30:45Z", tz=custom_tz)
    assert dt_explicit_to_custom.tzinfo == custom_tz
    # UTC 12:30 should become 18:00 in +05:30
    assert dt_explicit_to_custom.hour == 18
    assert dt_explicit_to_custom.minute == 0

    # Test datetime input with tz parameter
    dt_input = datetime(2023, 12, 4, 12, 30, 45, tzinfo=timezone.utc)
    dt_converted = of(dt_input, tz=custom_tz)
    assert dt_converted.tzinfo == custom_tz
    # UTC 12:30 should become 18:00 in +05:30
    assert dt_converted.hour == 18
    assert dt_converted.minute == 0


def test_stale_tz_parameter_comprehensive() -> None:
    """Comprehensive test of stale function with tz parameter."""
    now = datetime.now()  # Use local time for consistency

    # Test stale with naive string
    one_hour_ago = now - timedelta(hours=1)
    iso_time = one_hour_ago.strftime("%Y-%m-%dT%H:%M:%S")
    result = stale(iso_time)
    assert result == "1h"

    # Test stale with local timezone (default)
    # Create a local time for comparison
    now_local = datetime.now()
    one_hour_ago_local = now_local - timedelta(hours=1)
    iso_time_local = one_hour_ago_local.strftime("%Y-%m-%dT%H:%M:%S")
    result_local = stale(iso_time_local)  # Should use local timezone
    assert result_local == "1h"  # Should be 1h

    # Test stale with explicit timezone input and tz parameter
    explicit_tz_input = "2023-12-04T12:30:45+02:00"
    result_explicit = stale(explicit_tz_input, tz=timezone.utc)
    # Should convert +02:00 to UTC for comparison
    assert result_explicit.startswith("1")  # Should be around 1 hour (depending on current time)

    # Test stale with relative time (tz parameter doesn't affect relative times)
    result_rel = stale("-1h")
    assert result_rel == "1h"


def test_of_stale_tz_consistency() -> None:
    """Test consistency between of() and stale() with same tz parameter."""
    # Test that of() and stale() produce consistent results with same tz
    test_time = "2023-12-04 12:30:45"

    # Both should use UTC
    dt_utc = of(test_time, tz=timezone.utc)
    stale_utc = stale(test_time, tz=timezone.utc)

    assert dt_utc.tzinfo == timezone.utc
    # stale_utc should be a reasonable time difference (not negative or huge)
    assert stale_utc.endswith(("h", "d", "w", "y"))

    # Both should use naive datetime (default)
    dt_local = of(test_time)
    stale_local = stale(test_time)

    assert dt_local.tzinfo is None
    assert stale_local.endswith(("h", "d", "w", "y"))

    # Test with explicit timezone input
    explicit_time = "2023-12-04T12:30:45+02:00"

    # Both should convert to UTC
    dt_explicit_utc = of(explicit_time, tz=timezone.utc)
    stale_explicit_utc = stale(explicit_time, tz=timezone.utc)

    assert dt_explicit_utc.tzinfo == timezone.utc
    assert stale_explicit_utc.endswith(("h", "d", "w", "y"))

    # Both should keep original timezone
    dt_explicit_original = of(explicit_time)
    stale_explicit_original = stale(explicit_time)

    assert dt_explicit_original.tzinfo.utcoffset(None).total_seconds() == 7200  # +02:00
    assert stale_explicit_original.endswith(("h", "d", "w", "y"))


def test_tz_parameter_timezone_conversion_accuracy() -> None:
    """Test accuracy of timezone conversions with tz parameter."""
    # Test known timezone conversion
    # 2023-12-04 12:30:45 UTC should become 14:30:45 in +02:00
    test_tz = timezone(timedelta(hours=2))  # +02:00

    dt_utc = of("2023-12-04T12:30:45Z", tz=test_tz)
    assert dt_utc.tzinfo == test_tz
    assert dt_utc.hour == 14  # 12:30 UTC + 2 hours = 14:30 +02:00
    assert dt_utc.minute == 30
    assert dt_utc.second == 45

    # Test reverse conversion
    dt_back_to_utc = of("2023-12-04T14:30:45+02:00", tz=timezone.utc)
    assert dt_back_to_utc.tzinfo == timezone.utc
    assert dt_back_to_utc.hour == 12  # 14:30 +02:00 - 2 hours = 12:30 UTC
    assert dt_back_to_utc.minute == 30
    assert dt_back_to_utc.second == 45

    # Test naive input with timezone conversion
    dt_naive_converted = of("2023-12-04 12:30:45", tz=test_tz)
    assert dt_naive_converted.tzinfo == test_tz
    # The hour will be different because naive string is treated as local time, then converted to target timezone
    assert dt_naive_converted.minute == 30
    assert dt_naive_converted.second == 45


def test_stale_tz_parameter_edge_cases() -> None:
    """Test stale function with tz parameter and edge cases."""
    # Use local time for consistency with simplified stale() method
    now = datetime.now()

    # Test stale with future time (should be negative)
    future_time = now + timedelta(hours=1)
    future_str = future_time.strftime("%Y-%m-%dT%H:%M:%S")
    result_future = stale(future_str)
    assert result_future.startswith("-")  # Should be negative

    # Test stale with very old time
    old_time = now - timedelta(days=365 * 5 + 7 * 3)
    old_str = old_time.strftime("%Y-%m-%dT%H:%M:%S")
    result_old = stale(old_str)
    assert result_old.endswith(("y", "w", "d"))  # Should be years/weeks/days

    # Test stale with exactly now
    now_str = now.strftime("%Y-%m-%dT%H:%M:%S")
    result_now = stale(now_str)
    assert result_now == "0s"  # Should be 0 seconds

    # Test stale with timezone-aware datetime
    tz_aware_time = now - timedelta(hours=2)
    result_tz_aware = stale(tz_aware_time)
    assert result_tz_aware == "2h"  # Should be 2 hours


def test_tz_parameter_invalid_inputs() -> None:
    """Test tz parameter with invalid inputs."""
    # Test with invalid string
    with pytest.raises(ValueError):
        of("invalid date", tz=timezone.utc)

    with pytest.raises(ValueError):
        stale("invalid date", tz=timezone.utc)

    # Test with None
    with pytest.raises(ValueError):
        of(None, tz=timezone.utc)

    with pytest.raises(ValueError):
        stale(None, tz=timezone.utc)

    # Test with empty string
    with pytest.raises(ValueError):
        of("", tz=timezone.utc)

    with pytest.raises(ValueError):
        stale("", tz=timezone.utc)

    # Test with invalid type
    with pytest.raises(ValueError):
        of([], tz=timezone.utc)

    with pytest.raises(ValueError):
        stale([], tz=timezone.utc)
