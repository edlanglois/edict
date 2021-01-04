"""IO Protocols"""
from __future__ import annotations

import re
from typing import Callable, Dict, Iterable, List, TextIO

from edict.types import Record, RecordStream

__all__ = [
    "READERS",
    "WRITERS",
    "read_csv",
    "write_csv",
]


def _validated_records(records: Iterable[Record]) -> Iterable[Record]:
    for record in records:
        if None in record:
            values = record[None]  # type: ignore
            raise ValueError(
                f"Encountered value(s) {values} not in a named CSV column."
            )
        yield record


def read_csv(f: TextIO) -> RecordStream:
    import csv

    reader = csv.DictReader(f)
    fields = reader.fieldnames
    if fields is None:
        raise ValueError("First line must contain field names.")

    return RecordStream(fields=list(fields), records=_validated_records(reader))


def write_csv(f: TextIO, data: RecordStream) -> None:
    import csv

    writer = csv.DictWriter(f, data.fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(data.records)


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


def write_hledger_journal(f: TextIO, data: RecordStream) -> None:
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
    # If currency matches then must quote it
    # See isNonsimpleCommodityChar in hledger source
    quote_currency_match = re.compile(r'[-+\d\s.@*;"}{=]')

    for record in data.records:
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
        if quote_currency_match.search(default_currency):
            default_currency = '"' + default_currency + '"'

        for n in _get_hledger_posting_numbers(record):
            # _get_hledger_posting_numbers should only return values that exist
            account = record[f"account{n}"]
            if not account:
                continue

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
            elif quote_currency_match.search(currency):
                currency = f'"{currency}"'

            amount = record.get(f"amount{n}", "")
            if amount:
                if currency:
                    # If the length of the currency field is > 1 then it's probably a
                    # commodity rather than a currency symbol so separate from the
                    # amount with a space.
                    currency_sep = " " if len(currency) > 1 else ""
                    amount = f"{currency}{currency_sep}{amount}"

                if unitprice := record.get(f"unitprice{n}"):
                    amount = f"{amount} @ {unitprice}"
                elif totalprice := record.get(f"totalprice{n}"):
                    amount = f"{amount} @@ {totalprice}"

            balance = record.get(f"balance{n}", "")
            if balance and currency:
                balance = f"{currency}{balance}"
            if balance:
                balance = f" = {balance}"

            if suffix := f"{amount}{balance}{comment}":
                suffix = f"  {suffix}"

            f.write(f"    {status}{account}{suffix}\n")
        f.write("\n")


_Reader = Callable[[TextIO], RecordStream]
_Writer = Callable[[TextIO, RecordStream], None]

READERS: Dict[str, _Reader] = {
    "csv": read_csv,
}
WRITERS: Dict[str, _Writer] = {
    "csv": write_csv,
    "hledger": write_hledger_journal,
}
