import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.clean.salary import parse_salary

M = 1_000_000
USD = 25_400


def test_negotiable():
    for raw in ["Thoả thuận", "Sign in to view salary", "Negotiable", "Cạnh tranh"]:
        s = parse_salary(raw)
        assert s.disclosed is False and s.min_vnd is None and s.max_vnd is None


def test_usd_range():
    s = parse_salary("$1,000 - $2,000")
    assert s.currency == "USD" and s.min_vnd == 1000 * USD and s.max_vnd == 2000 * USD


def test_usd_upper_bound():
    s = parse_salary("Tới 1,500 USD")
    assert s.min_vnd is None and s.max_vnd == 1500 * USD


def test_vnd_million_range():
    s = parse_salary("10 - 20 triệu")
    assert s.min_vnd == 10 * M and s.max_vnd == 20 * M


def test_vnd_lower_bound():
    s = parse_salary("Trên 20 triệu")
    assert s.min_vnd == 20 * M and s.max_vnd is None


def test_single_value():
    s = parse_salary("15 triệu")
    assert s.min_vnd == s.max_vnd == 15 * M


def test_raw_vnd_number():
    s = parse_salary("20.000.000 VND")
    assert s.max_vnd == 20 * M


def test_mid():
    s = parse_salary("10 - 20 triệu")
    assert s.mid_vnd == 15 * M


def test_empty():
    assert parse_salary(None).disclosed is False
