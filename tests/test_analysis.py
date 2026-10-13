import unittest
import numpy as np
import pandas as pd
from analysis import clean_data, distribution, DOMAINS


class SurveyChecks(unittest.TestCase):
    def test_weighted_denominator_retains_unknown_and_missing(self):
        responses = pd.Series(["Positive", "Negative", "Don't know", pd.NA])
        weights = pd.Series([1., 2., 3., 4.])
        result = distribution(responses, weights, ["Positive", "Negative", "Don't know", "Missing"]).set_index("response")
        self.assertEqual(result.loc["Positive", "weighted_pct"], 10)
        self.assertEqual(result.loc["Missing", "weighted_pct"], 40)
        self.assertEqual(result.loc["Positive", "unweighted_pct"], 25)

    def test_zero_negative_and_missing_weights_fail(self):
        for bad in [0., -1., np.nan, np.inf]:
            with self.assertRaises(ValueError):
                distribution(pd.Series(["Yes", "No"]), pd.Series([1., bad]), ["Yes", "No"])

    def test_misaligned_rows_fail(self):
        with self.assertRaises(ValueError):
            distribution(pd.Series(["Yes"], index=[1]), pd.Series([1.], index=[2]), ["Yes"])

    def test_no_silent_category_loss(self):
        with self.assertRaises(ValueError):
            distribution(pd.Series(["Unexpected"]), pd.Series([1.]), ["Yes"])

    def fixture(self):
        return pd.DataFrame({"RESPONSEID": [1, 2], "WAVE": ["WAVE 3"]*2,
            "Weights": [1., 1.], "dAgeBand": ["18-24", "80+"],
            "Q21": ["I have never heard of AI"]*2,
            **{code: [" Slightly positive ", "Don't know"] for code in DOMAINS}})

    def test_cleaning_preserves_missing_and_unknown_answers(self):
        raw = self.fixture(); raw.loc[0, "Q25b_1"] = " "
        data, audit = clean_data(raw)
        self.assertTrue(pd.isna(data.loc[0, "Q25b_1"]))
        self.assertEqual(data.loc[1, "Q25b_1"], "Don't know")
        self.assertEqual(data.loc[0, "Q25b_2"], "Slightly positive")
        self.assertEqual(audit["missing_selected_answers"]["Q25b_1"], 1)

    def test_duplicate_ids_fail_instead_of_being_deleted(self):
        raw = self.fixture(); raw.loc[1, "RESPONSEID"] = 1
        with self.assertRaises(ValueError):
            clean_data(raw)

    def test_unknown_label_fails_before_mapping(self):
        raw = self.fixture(); raw.loc[0, "Q25b_1"] = "Typo"
        with self.assertRaises(ValueError):
            clean_data(raw)


if __name__ == "__main__":
    unittest.main()
