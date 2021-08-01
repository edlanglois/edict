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

# Check if amount is greater than 0.
# Numerical comparison because one side is a number.
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

## Specification

### Literals
Literals are used for expressing a value in an expression.
There are four literal types: String, Boolean, Number, and Regular Expression.

* String: A quoted UTF-8 string: `"some string"`
* Boolean: `true` or `false`
* Number: An high-precision decimal number with exact arithmetic.
          Not floating-point. Uses the Python [Decimal][decimal] type.
* Regular Expression: A Python [regular expression][regex]
          used only in match statements. Quoted with slashes (`/`):
          `/some regex *\d+/`.

[decimal]: https://docs.python.org/3/library/decimal.html
[regex]: https://docs.python.org/3/library/re.html#regular-expression-syntax

### Type System
Expressions and literals are strongly typed in Edict.
The possible types are `STRING`, `NUMBER`, `BOOLEAN`, `REGEX`, or `NONE` for
expressions with no value.
Implicit casting is never performed with these types and it is an error to use
a type where it is not expected.

Variables in Edict are weakly typed. All variables are stored as strings and
have the type `INDETERMINANT_STRING`, which is implicitly cast to `STRING` or
`NUMBER` depending on context. For example, `var == "0.0"` interprets `var`
as a string while `var == 0.0` interprets `var` as a number.
The inferred type of a variable does not persist between uses in a program, even
within the same statement, so the expression `var == 0 or var == "1"` is legal.

When the context is ambiguous, like in `var1 == var2`, variables are interpreted
as `STRING`. The `as_number` function can be used to explicitly cast variables
as `NUMBER`.

### Directives
Directives are special function calls that can be evaluated before running.
They may affect the structure of the edict program.

#### Header Directives
Header directives appear at the top of the file and establish some context for
the program.

* `@case_insensitive`
  Ignore case for string matching and comparisons.

* `@default_field(field)`
   Use the field `field` with implicit match statements.

* `@output_fields(field1, field2, ...)`
   Restrict the output fields. Only the matching field names will be included
   in the output (for outputs with configurable output fields).
   Currently, only applies to CSV output.

* `@reverse`
   Reverse the order of the input records.

#### Inline Directives
Inline directives can go anywhere a regular statement goes.

* `@@import("relative/path/to/script.edt")`
   Import another edict script and apply it at this location.

### Builtin Functions
The available functions are:

* `as_number(x) -> NUMBER`
   Interpret the value `x` as a number.
   This is useful when comparing two variables to force numeric comparisons.
   For example, `a == b` does string comparison while `as_number(a) == b`
   does numeric comparison.

* `log(arg1, arg2, ...)`
   Log all arguments to standard error when executed.
   Takes any number of arguments.

* `read_date(date_string: STRING, format_string: STRING) -> STRING`
   Read a date a format as an ISO 8601 string.
   The format string is the same used by [Python strptime][spt]

* `record_str() -> STRING`
   Format the current record as a string.
   Used for debugging with `log(record_str())`.

* `substring(string: STRING, start: NUMBER, end: NUMBER) -> NUMBER`
   The sub-string of `string` from `start` (inclusive) to `end` (exclusive).
   Negative indices count from the end. The last character has index `-1`.
   Equivalent to the Python expression `string[start:end]`.

[spt]: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior

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
