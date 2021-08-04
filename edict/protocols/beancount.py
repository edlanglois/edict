"Beancount IO Protocols"
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, TextIO

from ..types import Record, RecordStream

__all__ = ["write_beancount_journal"]


def _get_beancount_posting_numbers(fields: Iterable[str]) -> List[int]:
    prefix = "account"
    prefix_len = len(prefix)
    posting_numbers = set()
    for field in fields:
        if not field.startswith(prefix):
            continue
        try:
            n = int(field[prefix_len:])
        except ValueError:
            pass
        else:
            if n >= 0:
                posting_numbers.add(n)
    return list(sorted(posting_numbers))


def write_beancount_journal(f: TextIO, data: RecordStream, args: Dict) -> None:
    """Write an beancount journal file.

    Format Specification:
    https://beancount.org/1.18/journal.html

    Rules:
    * Posting lines are identified by a nonnegative integer suffix N
    * An account line is written if and only if `accountN` is non-empty
    * Some values in the posting line use `nameN` if non-empty otherwise `name`
    * If both `nameN` and `name` are empty then the value is ommitted (include `amount`)

    The caller is responsible for ensuring that record values are appropriate.
    For example, date must be formatted as YYYY-MM-DD (or / or . instead of -)
    """

    for record in data.records:
        _write_record(f, record)


def _record_value(
    record: Record, key: str, fmt: Optional[str] = None, default: str = ""
) -> str:
    value = record.get(key, default)
    if value is None:
        value = default
    if value and fmt is not None:
        value = fmt.format(value)
    return value


def _write_record(f: TextIO, record: Record) -> None:
    """Write a record as a Beancount directive"""
    directive = record.get("directive", "")
    if directive in ("", "*", "txn", "transaction"):
        _write_transaction(f, record)
    elif directive == "open":
        date = record["date"]
        account = record["account"]
        currency = _record_value(record, "currency", " {}")
        booking_method = _record_value(record, "booking method", ' "{}"')
        comment = _record_value(record, "comment", "; {}")
        f.write(f"{date} open {account}{currency}{booking_method}{comment}\n")
    elif directive == "close":
        date = record["date"]
        account = record["account"]
        f.write(f"{date} close {account}\n")
    else:
        raise ValueError(f"Invalid directive type {directive!r}")


def _write_transaction(f: TextIO, record: Record) -> None:
    """Write a record as an beancount transaction."""
    date = record["date"]  # required
    payee = ""
    if description := _record_value(record, "description", ' "{}"'):
        payee = _record_value(record, "payee", " {}")
    comment = _record_value(record, "comment", " ; {}")
    f.write(f"{date} txn{payee}{description}{comment}\n")

    default_currency = _record_value(record, "currency")

    for n in _get_beancount_posting_numbers(record):
        _write_posting(f, record, n, default_currency)
    f.write("\n")


def _write_posting(f: TextIO, record: Record, n: int, default_currency: str) -> None:
    """Write the n-th posting of an beancount transaction."""
    # _get_beancount_posting_numbers should only return values that exist
    account = record[f"account{n}"]
    if not account:
        return

    status = _record_value(record, f"status{n}", " {}")
    comment = _record_value(record, f"comment{n}", " ; {}")

    if record.get(f"virtual{n}"):
        account = f"({account})"
    elif record.get(f"balanced virtual{n}"):
        account = f"[{account}]"

    currency = record.get(f"currency{n}")
    if not currency:
        currency = default_currency

    price_currency = record.get(f"pricecurrency{n}")
    if not price_currency:
        price_currency = default_currency

    amount = record.get(f"amount{n}", "")
    if amount:
        if currency:
            amount = f"{amount} {currency}"

        if lotunitprice := record.get(f"lotunitprice{n}"):
            if lotunitprice == "IMPLICIT":
                amount = f"{amount} {{}}"
            else:
                if price_currency:
                    lotunitprice = f"{lotunitprice} {price_currency}"
                amount = f"{amount} {{{lotunitprice}}}"

        if unitprice := record.get(f"unitprice{n}"):
            if price_currency:
                unitprice = f"{unitprice} {price_currency}"
            amount = f"{amount} @ {unitprice}"

    # TODO: Support balances

    if suffix := f"{amount}{comment}":
        suffix = f"  {suffix}"

    f.write(f"    {status}{account}{suffix}\n")
