---
name: csv-analyzer
description: Analyze a CSV file — shape, missing values, numeric stats, top categories, and data-quality warnings.
triggers: csv, spreadsheet, dataframe, columns, dataset, rows, analyze data, tabular
risk: safe
mode: action
version: 1
---

# CSV Analyzer

Turn a raw CSV into a quick, honest data profile. Use this whenever someone
mentions a CSV, a spreadsheet export, or "my data file".

## Steps

1. Read the file with Python's `csv` module (never load the whole file into
   a prompt — files can be huge).
2. Report the **shape**: number of data rows and columns.
3. List each column with its inferred type:
   - numeric if ≥80% of non-empty values parse as float,
   - otherwise categorical/text.
4. For every column, report **missing values** (empty string or `NA`-style
   tokens) as both a count and a percentage.
5. For numeric columns: min, max, mean, median, and a simple standard
   deviation. Flag anything that looks wrong:
   - negative values in a column that shouldn't be negative (ages, prices),
   - a max that is 10× the median (likely a typo like `10000` instead of `100`),
   - a constant column (zero variance — it carries no information).
6. For categorical columns: the top 5 values with counts, and how many
   distinct values exist.
7. End with a **data-quality verdict**: a one-line summary plus the top 3
   things to fix before this data is used for modeling or reporting.

## Output format

```
SHAPE       <rows> rows × <cols> columns
COLUMNS     <name> (<type>) — <missing%> missing
            ...
STATS       <numeric column>: min=… max=… mean=… median=… std=…
TOP VALUES  <categorical column>: value (n), value (n), ...
WARNINGS    - <issue>
            - <issue>
VERDICT     <one line>
```

## Rules

- Never silently drop rows; report what you found.
- Percentages to one decimal place.
- If the file has no header row, say so and treat the first row as data.
- If the CSV cannot be parsed at all, explain the exact failure (bad quoting,
  ragged rows) instead of showing a traceback.
