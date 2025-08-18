"HLedger Output Protocol"

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, TextIO

from ..types import Record, RecordStream

__all__ = ["write_hledger_journal"]


def _get_hledger_posting_numbers(fields: Iterable[str]) -> List[int]:
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


# If currency matches then must quote it
# See isNonsimpleCommodityChar in hledger source
_QUOTE_CURRENCY_PATTERN = re.compile(r'[-+\d\s.@*;"}{=]')


def write_hledger_journal(f: TextIO, data: RecordStream, args: Dict) -> None:
    """Write an hledger journal file.

    Format Specification:
    https://hledger.org/1.18/journal.html

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


def _write_record(f: TextIO, record: Record) -> None:
    """Write a record as an hledger transaction."""
    date = record["date"]  # required
    if date2 := record.get("date2", ""):
        date2 = f"={date2}"
    if status := record.get("status", ""):
        status = f" {status}"
    if code := record.get("code", ""):
        code = f" ({code})"
    if description := record.get("description", ""):
        description = f" {description}"
    if comment := record.get("comment", ""):
        comment = f"  ; {comment}"
    f.write(f"{date}{date2}{status}{code}{description}{comment}\n")

    default_currency = record.get("currency", "")
    if _QUOTE_CURRENCY_PATTERN.search(default_currency):
        default_currency = '"' + default_currency + '"'

    for n in _get_hledger_posting_numbers(record):
        _write_posting(f, record, n, default_currency)
    f.write("\n")


def _with_currency(amount: str, currency: Optional[str]) -> str:
    """Format an amount with a currency or commodity."""
    if currency is None:
        return amount
    # If the length of the currency field is > 1 then it is probably a
    # commodity rather than a currency symbol so separate from the
    # amount with a space.
    currency_sep = " " if len(currency) > 1 else ""
    return f"{currency}{currency_sep}{amount}"


def _write_posting(f: TextIO, record: Record, n: int, default_currency: str) -> None:
    """Write the n-th posting of an hledger transaction."""
    # _get_hledger_posting_numbers should only return values that exist
    account = record[f"account{n}"]
    if not account:
        return

    if status := record.get(f"status{n}", ""):
        status = f" {status}"

    if comment := record.get(f"comment{n}", ""):
        comment = f"  ; {comment}"

    if record.get(f"virtual{n}"):
        account = f"({account})"
    elif record.get(f"balanced virtual{n}"):
        account = f"[{account}]"

    currency = record.get(f"currency{n}")
    if not currency:
        currency = default_currency
    elif _QUOTE_CURRENCY_PATTERN.search(currency):
        currency = f'"{currency}"'

    price_currency = record.get(f"pricecurrency{n}")
    if not price_currency:
        price_currency = default_currency
    elif _QUOTE_CURRENCY_PATTERN.search(currency):
        price_currency = f'"{price_currency}"'

    amount = record.get(f"amount{n}", "")
    if amount:
        amount = _with_currency(amount, currency)

        if unitprice := record.get(f"unitprice{n}"):
            amount = f"{amount} @ {_with_currency(unitprice, price_currency)}"
        elif totalprice := record.get(f"totalprice{n}"):
            amount = f"{amount} @@ {_with_currency(totalprice, price_currency)}"

    balance = record.get(f"balance{n}", "")
    if balance and currency:
        balance = f"{currency}{balance}"
    if balance:
        balance = f" = {balance}"

    if suffix := f"{amount}{balance}{comment}":
        suffix = f"  {suffix}"

    f.write(f"    {status}{account}{suffix}\n")
