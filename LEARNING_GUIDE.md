# Analysis walkthrough

This guide explains the research questions, denominators, response recoding, survey weights and limitations, with examples for reproducing and extending the analysis.

## 1. Run it and inspect the inputs

Follow the README setup, then open `analysis.py` alongside the source workbook's `Datamap` sheet. Trace `Q25b_7` from its original label to the crime chart. Notice that one row is one respondent and one column is one question or attribute.

In a Python session launched from the project folder, try:

```python
import pandas as pd
data = pd.read_excel('data/raw/wave3_cawi.xlsx', sheet_name='Data')
print(data.shape)
print(data['Q25b_7'].value_counts(dropna=False))
print(data['Weights'].describe())
```

Explain why the first number in `shape` is 4,225. Then explain why an age group has a smaller base.

## 2. Calculate one percentage before reading the function

```python
positive = data['Q25b_7'].isin(['Very positive', 'Slightly positive'])
unweighted = 100 * positive.mean()
weighted = 100 * data.loc[positive, 'Weights'].sum() / data['Weights'].sum()
print(unweighted, weighted)
```

`isin` returns one True/False value for each respondent. The mean of that mask is the ordinary proportion. The weighted calculation changes each person's contribution using the publisher's weight.

For a hand calculation, suppose responses are Positive, Negative, Don't know, Missing and weights are 1, 2, 3, 4. The positive share is 1/10 = 10%, not 1/4 = 25%. Dropping unknown and missing responses would change the question and denominator.

## 3. Understand cleaning

Find `clean_data`. Explain these decisions:

- Spaces around a label are formatting noise and can be stripped.
- `Don't know` is a real answer, not an empty cell.
- An unfamiliar label might be a changed questionnaire, so the program stops.
- Duplicate IDs are flagged rather than silently deleted.
- Zero, missing, negative and infinite weights are rejected.
- The program analyses selected columns only. It does not claim to clean the entire workbook.

There are no missing answers in the selected survey variables. The unit tests create missing values on purpose to demonstrate correct behaviour.

## 4. Read a chart critically

For each chart, identify the population, collection period, question, denominator and weighting. Explain why the crime question is not evidence that people support every AI use in policing, courts or prisons.

Look at `official_checks.csv`. A difference of 0.4 percentage points can agree with a published whole-number percentage. It is not evidence of a statistically significant difference. Comparing a result with an independent source is stronger than only checking that your own percentages sum to 100.

## 5. Possible extensions

The following exercises extend the baseline analysis. Rerun the tests and document any changes to the outputs:

1. Recalculate the crime chart using the negative response category. Change its title and labels as well as its data. Check it against the negative rows in official Table 118.
2. Produce a weighted/unweighted comparison for fair treatment. Explain why the two values differ and why weighting does not make the sample perfect.
3. Calculate a second, clearly labelled percentage among only respondents with a positive, neutral or negative view. Keep the original all-respondent result and explain why excluding Don't know changes the interpretation.

Do not replace the baseline outputs without recording the change. Use a new filename, such as `crime_negative_by_age.png`. Record changes and verification results in `REVIEW_LOG.md`.

## 6. Explaining the analysis

Answer these in your own words:

- Why did you use this dataset and this question?
- What do `groupby`, a Boolean mask and a survey weight do?
- Why didn't you drop Don't know responses?
- What error would occur if you divided each age group's positive count by the full sample?
- Which checks would catch an unexpected label or mismatched rows?
- Why are these results descriptive and historical?
- What did the checks establish, and what limitations remain?

For unfamiliar code, work through a small example to see how the calculation behaves.

## Project summary

This project uses pandas and Matplotlib to explore public attitudes to AI, applying survey weights, checking denominators and comparing results with published tables.
