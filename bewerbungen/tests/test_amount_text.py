"""#339, G45: amounts and durations the server writes read like the pages' cost lines (treffer-logik.js)."""
import amount_text

NBSP = " "


def test_the_currency_comes_first_and_stays_with_the_amount():
    assert amount_text.money_text(0.05, "CHF") == f"CHF{NBSP}0.05"
    assert amount_text.money_text(1.234, "USD") == f"USD{NBSP}1.23"


def test_minutes_stay_with_their_number_and_count_one_alone():
    assert amount_text.minutes_text(23) == f"23{NBSP}Minuten"
    assert amount_text.minutes_text(1) == f"1{NBSP}Minute"


def test_seconds_stay_with_their_number_and_count_one_alone():
    assert amount_text.seconds_text(30) == f"30{NBSP}Sekunden"
    assert amount_text.seconds_text(1) == f"1{NBSP}Sekunde"
