---
name: unit-convert
description: Convert between units — length, mass, temperature, data size, time, and speed — with exact factor math.
triggers: convert, conversion, units, km, miles, kg, pounds, celsius, fahrenheit, mb, gigabytes
risk: safe
mode: action
version: 1
---

# Unit Convert

Convert a value from one unit to another with real precision, not a
language-model guess.

## Steps

1. Parse the request: value, source unit, target unit.
2. Match the unit name (case-insensitive) against the unit table:
   - aliases count (`km` = `kilometer` = `kilometre`, `lbs` = `pound`),
   - temperature uses offset formulas (see below), everything else is a
     simple factor: `target = value × factor(source) ÷ factor(target)`.
3. Temperature is special:
   - to Celsius: `°F → (f − 32) × 5/9`, `K → k − 273.15`
   - from Celsius: `→ °F = c × 9/5 + 32`, `→ K = c + 273.15`
   - converting F↔K goes through Celsius as the pivot.
4. Round to a sensible precision: 4 significant digits, trailing zeros
   stripped (never print `3.2808` when `3.28` says the same thing).
5. Show the work: the factor used and the one-line formula.

## Output format

```
<value> <source> = <result> <target>
how: <value> × <factor expression>  (rounded to 4 sig figs)
```

## Rules

- Reject unknown units by listing the supported families.
- Zero and negatives are valid inputs (temperatures below zero exist).
- Never guess a factor from memory in LLM mode if the action exists —
  the action's table is the source of truth.
