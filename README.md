# edict: Eric's Dictionary Transformer
A simple language for specifying transformations to dictionaries
(also called records or key-value-stores).

An edict program describes a series of rules and assignments that are applied to
a set of records on a record-by-record basis.
All variables refer to keys in the current record.
Variables values are always stored as strings but certain operations
(like math) interpret the variable values as other types.
Uninitialized variables are empty strings.

The syntax of edict is loosely based on Python and Bash. Whitespace is ignored.

This is in alpha stage. Changes may be backwards incompatible without warning.

## Example
The following is a simple script for categorizing transactions.
```sh
# This is a comment
@case_insensitive              # ignore case when matching
@default_field("description")  # use the key "description" for implicit matches

# Use the 'read_date' builtin function to convert DD/MM/YYYY to the standard
# YYYY-MM-DD. The format codes are those used by Python's strptime format
# https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
date = read_date(date, "%d/%m/%Y")

# Check if "moe's tavern" is a substring of the "description" variable
if "moe's tavern" then         
    account = "Expenses:Drinks"

# Check if amount is greater than 0. Numerical comparison, not string comparison.
# There are no string comparisons in edict.
elif amount > 0 then
    account = "Income:Uncategorized"
else
    account = "Expenses:Uncategorized"
fi
```

See the `.edt` files in [tests/files](tests/files) for more examples.

## Install
```sh
pip install .
```

## Development
### Editable Install
```sh
python setup.py develop [--user]
```
Re-run this command to refresh the version number (based on git tags).

### Versioning
Uses [Semantic Versioning](https://semver.org/).

Versions are set exclusively via git tags:
```sh
git -a v0.1.2 -m "Version 0.1.2"
```
