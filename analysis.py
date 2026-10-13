"""Reproduce a small descriptive analysis of the public CDEI Wave 3 survey.

Python survey analysis project by Maham Sufi. See README.md for methods.
Run: python analysis.py
"""
from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache" / "matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DOMAINS = {
    "Q25b_1": "Fair treatment in society",
    "Q25b_2": "Everyday tasks",
    "Q25b_4": "Job opportunities",
    "Q25b_5": "Healthcare",
    "Q25b_6": "Education",
    "Q25b_7": "Crime prevention and detection",
    "Q25b_8": "Affordability of goods and services",
}
IMPACT = {
    "Very negative": "Negative", "Slightly negative": "Negative",
    "Neither positive nor negative": "Neutral",
    "Slightly positive": "Positive", "Very positive": "Positive",
    "Don't know": "Don't know",
}
AWARENESS = [
    "I have never heard of AI",
    "I have heard of AI but could not explain what it is",
    "I have heard of AI and could give a partial explanation of what it is",
    "I have heard of AI and could explain what it is in detail",
]
CATEGORIES = ["Negative", "Neutral", "Positive", "Don't know", "Missing"]
AGES = {
    "18-24": "18–34", "25-34": "18–34", "35-44": "35–54", "45-54": "35–54",
    "55-64": "55+", "65-69": "55+", "70-74": "55+", "75-79": "55+", "80+": "55+",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean_data(raw):
    """Select columns, standardise whitespace and validate without inventing values."""
    columns = ["RESPONSEID", "WAVE", "Weights", "dAgeBand", "Q21", *DOMAINS]
    missing = set(columns) - set(raw.columns)
    if missing:
        raise ValueError(f"Required columns missing: {sorted(missing)}")
    data = raw[columns].copy()
    for col in ["WAVE", "dAgeBand", "Q21", *DOMAINS]:
        data[col] = data[col].astype("string").str.replace("\u00a0", " ").str.strip()
        data[col] = data[col].replace("", pd.NA)
    if data.RESPONSEID.isna().any() or data.RESPONSEID.duplicated().any():
        raise ValueError("Missing or duplicate respondent IDs: investigate the source.")
    if data.WAVE.isna().any() or not data.WAVE.eq("WAVE 3").all():
        raise ValueError("Expected Wave 3 responses only.")
    data["Weights"] = pd.to_numeric(data.Weights, errors="raise")
    if not np.isfinite(data.Weights).all() or not data.Weights.gt(0).all():
        raise ValueError("Weights must be finite and strictly positive.")
    for col, allowed in [("dAgeBand", AGES), ("Q21", AWARENESS), *[(c, IMPACT) for c in DOMAINS]]:
        unknown = set(data[col].dropna().unique()) - set(allowed)
        if unknown:
            raise ValueError(f"Unexpected labels in {col}: {sorted(unknown)}")
    if data.dAgeBand.isna().any():
        raise ValueError("Missing age bands require an explicit subgroup policy.")
    data["age_group"] = data.dAgeBand.map(AGES)
    audit = {
        "respondents": len(data), "duplicate_ids": 0,
        "weight_sum": float(data.Weights.sum()),
        "weight_min": float(data.Weights.min()), "weight_max": float(data.Weights.max()),
        "missing_selected_answers": {c: int(data[c].isna().sum()) for c in ["Q21", *DOMAINS]},
        "missing_policy": "Keep blank answers as Missing; retain Don't know as a substantive category. No imputation.",
    }
    return data, audit


def distribution(responses, weights, categories):
    """Denominator is ALL respondents in this group, including missing and don't know."""
    if len(responses) == 0 or not responses.index.equals(weights.index):
        raise ValueError("Responses and weights must have matching nonempty indexes.")
    if not np.isfinite(weights).all() or not weights.gt(0).all():
        raise ValueError("Weights must be finite and positive.")
    labels = responses.fillna("Missing")
    if not set(labels.unique()).issubset(set(categories)):
        raise ValueError("Category list does not cover every response.")
    rows = []
    for category in categories:
        selected = labels.eq(category)
        rows.append({
            "response": category, "n": int(selected.sum()),
            "weighted_count": float(weights[selected].sum()),
            "weighted_pct": 100 * float(weights[selected].sum()) / float(weights.sum()),
            "unweighted_pct": 100 * float(selected.mean()),
            "base_n": len(labels), "weighted_base": float(weights.sum()),
        })
    result = pd.DataFrame(rows)
    if not np.isclose(result.weighted_pct.sum(), 100):
        raise ValueError("Percentages failed to reconcile.")
    return result


def calculate(data):
    parts = []
    for code, label in DOMAINS.items():
        tab = distribution(data[code].map(IMPACT), data.Weights, CATEGORIES)
        tab.insert(0, "domain", label)
        tab.insert(0, "variable", code)
        parts.append(tab)
    domains = pd.concat(parts, ignore_index=True)
    parts = []
    for age in ["18–34", "35–54", "55+"]:
        group = data[data.age_group.eq(age)]
        tab = distribution(group.Q25b_7.map(IMPACT), group.Weights, CATEGORIES)
        tab.insert(0, "age_group", age)
        parts.append(tab)
    crime_age = pd.concat(parts, ignore_index=True)
    awareness = distribution(data.Q21, data.Weights, AWARENESS + ["Missing"])
    return domains, crime_age, awareness


def verify_official(domains, crime_age, awareness, source):
    """Compare against independently published rounded percentages, not our own totals."""
    checks = []
    def compare(sheet, row_label, column, estimate):
        table = pd.read_excel(source, sheet_name=sheet, header=None)
        rows = table.index[table[1].astype(str).str.strip().eq(row_label)]
        if len(rows) != 1:
            raise ValueError(f"Cannot locate {row_label} in {sheet}")
        r = int(rows[0]) + 1  # source stores the percentage below the count
        published = float(table.iloc[r, column]) * 100
        error = abs(estimate - published)
        checks.append({"sheet": sheet, "label": row_label, "source_excel_cell": f"{'CDEF'[column-2]}{r+1}",
                       "calculated_pct": estimate, "published_pct": published,
                       "difference_pp": error, "pass": error <= 0.51})
    for sheet, code in zip(range(113, 120), DOMAINS):
        for category in ["Positive", "Negative"]:
            value = domains.loc[domains.variable.eq(code) & domains.response.eq(category), "weighted_pct"].item()
            compare(f"Table {sheet}", f"NET: {category}", 2, value)
    for age, col in [("18–34", 3), ("35–54", 4), ("55+", 5)]:
        value = crime_age.loc[crime_age.age_group.eq(age) & crime_age.response.eq("Positive"), "weighted_pct"].item()
        compare("Table 118", "NET: Positive", col, value)
    for category in AWARENESS:
        value = awareness.loc[awareness.response.eq(category), "weighted_pct"].item()
        compare("Table 106", category, 2, value)
    result = pd.DataFrame(checks)
    if not result["pass"].all():
        raise ValueError(f"Official benchmark disagreement:\n{result[~result['pass']]}")
    return result


def charts(domains, crime_age, out):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.spines.left": False})
    colours = {"Negative": "#B45243", "Neutral": "#D1D8DF", "Positive": "#267C73", "Don't know": "#798BA9", "Missing": "#E5C07B"}
    order = domains[domains.response.eq("Positive")].sort_values("weighted_pct", ascending=False).domain.tolist()
    fig, ax = plt.subplots(figsize=(12, 6.5))
    left = np.zeros(len(order))
    for category in CATEGORIES:
        values = domains[domains.response.eq(category)].set_index("domain").loc[order, "weighted_pct"].to_numpy()
        if not values.any():
            continue
        ax.barh(order, values, left=left, label=category, color=colours[category], height=.62)
        for i, value in enumerate(values):
            if value >= 6:
                ax.text(left[i] + value / 2, i, f"{value:.0f}%", ha="center", va="center",
                        color="#243040" if category == "Neutral" else "white", fontsize=10)
        left += values
    ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("Weighted share of all respondents (%)")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -.17), ncol=4, frameon=False)
    fig.suptitle("Expectations of AI differ across areas of life", x=.035, ha="left", fontsize=19, fontweight="bold")
    fig.text(.035, .905, "CDEI Wave 3 · UK online survey · August 2023 · n = 4,225", color="#52606D")
    fig.text(.035, .035, "Q25b. Positive and negative combine two response levels each. Don't know remains in the denominator.\nSource: CDEI / DSIT published microdata; descriptive calculations by Maham Sufi.", fontsize=9)
    fig.subplots_adjust(left=.31, right=.97, top=.83, bottom=.24)
    fig.savefig(out / "ai_impact_by_domain.png", dpi=180); plt.close(fig)

    selected = crime_age[crime_age.response.eq("Positive")]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    bars = ax.bar(selected.age_group, selected.weighted_pct, color="#267C73", width=.5)
    for bar, row in zip(bars, selected.itertuples()):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1, f"{row.weighted_pct:.1f}%", ha="center", fontweight="bold")
        ax.text(bar.get_x()+bar.get_width()/2, 3, f"n = {row.base_n:,}", ha="center", color="white")
    ax.set_ylim(0, 100); ax.set_ylabel("Weighted positive share (%)"); ax.set_xlabel("Age group")
    ax.grid(axis="y", alpha=.15); ax.set_axisbelow(True)
    fig.suptitle("Expected positive impact on crime prevention and detection", x=.04, ha="left", fontsize=16, fontweight="bold")
    fig.text(.04, .895, "August 2023 · Descriptive age comparison", color="#52606D")
    fig.text(.04, .035, "Q25b_7. Base: all respondents in each age group, including Don't know. Counts are unweighted.\nNo significance tests or causal claims. This question does not measure consent to specific justice systems.\nSource: CDEI / DSIT Wave 3 online microdata; descriptive calculations by Maham Sufi.", fontsize=9)
    fig.subplots_adjust(left=.1, right=.97, top=.8, bottom=.23)
    fig.savefig(out / "crime_expectations_by_age.png", dpi=180); plt.close(fig)


def report(domains, crime_age, awareness, audit, out):
    def pct(code, response):
        return domains.loc[domains.variable.eq(code) & domains.response.eq(response), "weighted_pct"].item()
    explain = awareness.loc[awareness.response.isin(AWARENESS[2:]), "weighted_pct"].sum()
    age = crime_age[crime_age.response.eq("Positive")].set_index("age_group").weighted_pct
    text = f'''# AI expectations and public services

A descriptive analysis of public attitudes to AI by Maham Sufi, using CDEI / DSIT Wave 3 survey data.

## Findings from the downloaded data

The weighted positive share is {pct('Q25b_2','Positive'):.1f}% for everyday tasks and {pct('Q25b_5','Positive'):.1f}% for healthcare. For fair treatment in society, {pct('Q25b_1','Positive'):.1f}% expect a positive impact and {pct('Q25b_1','Negative'):.1f}% a negative one. For job opportunities, the negative share is {pct('Q25b_4','Negative'):.1f}%.

For crime prevention and detection, {pct('Q25b_7','Positive'):.1f}% expect a positive impact, {pct('Q25b_7','Negative'):.1f}% a negative impact, {pct('Q25b_7','Neutral'):.1f}% are neutral and {pct('Q25b_7',"Don't know"):.1f}% select Don't know. Positive expectations are {age['18–34']:.1f}% among ages 18–34, {age['35–54']:.1f}% among ages 35–54 and {age['55+']:.1f}% among ages 55+. These are descriptive differences, not tests of significance. {explain:.1f}% report being able to explain AI at least partially; that is self-assessment, not a skills test.

## Interpretation for qualitative research

The pattern motivates asking participants about particular uses of AI rather than treating AI as one uniform intervention. Possible follow-up questions: What makes a use helpful? What could make it unfair? Who should explain or challenge a decision? These are suggested research questions, not findings about justice service users.

## Method and limits

Data are from the CDEI / DSIT Wave 3 online survey, fielded 11–23 August 2023. The {audit['respondents']:,} rows represent respondents. We use the supplied weights and divide each category's weight sum by the weight sum for all respondents in its group. Positive combines Very and Slightly positive; Negative combines Very and Slightly negative. Don't know is retained. Blank answers would remain a separate Missing category; none occur in the selected answers in this release. No responses were imputed or removed.

These are historical 2023 perceptions, not current views or measured effects of AI. The separate telephone sample is not included. The study uses an online quota sample; weighting does not remove all coverage or selection bias. No confidence intervals or population significance claims are made here. General expectations about crime do not establish approval of any specific AI tool, fairness, or outcomes for people using justice services.

## Verification

All 21 benchmark comparisons match the official rounded tables within 0.51 percentage points (the source reports whole percentages). See `official_checks.csv`, `quality_audit.json`, and `tests/test_analysis.py`. The weighted/unweighted columns expose the effect of weighting. Source URLs, workbook question labels and SHA-256 fingerprints are recorded in the repository.
'''
    (out / "FINDINGS.md").write_text(text, encoding="utf-8")


def main():
    manifest = json.loads((ROOT / "data/sources.json").read_text())
    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        if not path.exists():
            raise FileNotFoundError(f"Run python download_data.py first. Missing {path.name}")
        if sha256(path) != entry["sha256"]:
            raise ValueError(f"Source changed: {path.name}. Review before updating its fingerprint.")
    raw = pd.read_excel(ROOT / "data/raw/wave3_cawi.xlsx", sheet_name="Data")
    data, audit = clean_data(raw)
    if len(data) != 4225:
        raise ValueError("Unexpected respondent count for this release.")
    domains, crime_age, awareness = calculate(data)
    checks = verify_official(domains, crime_age, awareness, ROOT / "data/raw/wave3_weighted_tables.xlsx")
    out = ROOT / "outputs"; out.mkdir(exist_ok=True)
    for name, frame in [("domain_distribution", domains), ("crime_by_age", crime_age), ("ai_awareness", awareness), ("official_checks", checks)]:
        frame.to_csv(out / f"{name}.csv", index=False, float_format="%.6f")
    audit["official_benchmarks_passed"] = int(checks["pass"].sum())
    (out / "quality_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    dictionary = pd.read_excel(ROOT / "data/raw/wave3_cawi.xlsx", sheet_name="Datamap")
    dictionary[dictionary["Variable Name"].isin(["Weights", "dAgeBand", "Q21", *DOMAINS])].to_csv(out / "selected_variable_dictionary.csv", index=False)
    charts(domains, crime_age, out)
    report(domains, crime_age, awareness, audit, out)
    print(f"Analysed {len(data):,} respondents. {len(checks)} official checks passed. Outputs: {out}")


if __name__ == "__main__":
    main()
