"""Tests for pipeline.pacing — the logic behind what gets built and when.

Run with:  python -m unittest discover -s tests
"""

import doctest
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pipeline.pacing as pacing  # noqa: E402
from pipeline.pacing import (  # noqa: E402
    best_expandable_power, contrast_fractions, desuperscript, divides_visibly,
    emphasis_words, expand_power, factor_tree, fill_times, find_composites,
    find_fractions, find_powers, is_terminating, lesson_vocabulary,
    long_division, prime_factorization, split_latex_parts,
)


def load_tests(loader, tests, ignore):
    """Run the module's doctests as part of the suite."""
    tests.addTests(doctest.DocTestSuite(pacing))
    return tests


class FillTimes(unittest.TestCase):
    def test_short_gap_needs_no_beat(self):
        self.assertEqual(fill_times(0.0, 3.0, 4.0), [])
        self.assertEqual(fill_times(0.0, 4.0, 4.0), [])

    def test_long_gap_is_broken_up(self):
        self.assertEqual(fill_times(0.0, 10.0, 4.0), [3.333, 6.667])

    def test_no_resulting_stretch_exceeds_the_budget(self):
        for span in (5.0, 9.5, 17.0, 31.4, 60.0):
            for budget in (2.0, 3.2, 5.0):
                marks = [0.0] + fill_times(0.0, span, budget) + [span]
                gaps = [b - a for a, b in zip(marks, marks[1:])]
                self.assertLessEqual(max(gaps), budget + 1e-6,
                                     f"span={span} budget={budget}")

    def test_beats_are_evenly_spaced(self):
        marks = fill_times(0.0, 12.0, 5.0)
        self.assertEqual(marks, [4.0, 8.0])


class SplitLatexParts(unittest.TestCase):
    def test_parts_rebuild_the_original(self):
        for latex in (r"a^m \cdot a^n = a^{m+n}",
                      r"\frac{p}{q}, q \neq 0",
                      r"(a^m)^n = a^{mn}",
                      r"x^2 \cdot x^3 = x^5"):
            self.assertEqual("".join(split_latex_parts(latex)), latex)

    def test_splits_at_top_level_joins(self):
        self.assertEqual(split_latex_parts(r"a^m \cdot a^n = a^{m+n}"),
                         ["a^m ", r"\cdot", " a^n ", "=", " a^{m+n}"])

    def test_never_splits_inside_braces(self):
        parts = split_latex_parts(r"a^{m+n} = b")
        self.assertIn("a^{m+n} ", parts)

    def test_never_splits_inside_a_fraction(self):
        parts = split_latex_parts(r"\frac{2^m}{5^n} = x")
        self.assertTrue(any(p.strip() == r"\frac{2^m}{5^n}" for p in parts))

    def test_leading_sign_is_not_a_join(self):
        self.assertEqual(split_latex_parts("-x = y")[0], "-x ")

    def test_atomic_expression_is_left_alone(self):
        self.assertEqual(split_latex_parts("x^2"), ["x^2"])
        self.assertEqual(split_latex_parts(""), [""])

    def test_control_word_prefixes_do_not_collide(self):
        # \leq must not be split as \le + "q"
        self.assertEqual("".join(split_latex_parts(r"a \leq b")), r"a \leq b")


class LongDivision(unittest.TestCase):
    def test_terminating_expansion(self):
        result = long_division(1, 8)
        self.assertEqual(result["steps"], ["0.", "0.1", "0.12", "0.125"])
        self.assertTrue(result["terminating"])
        self.assertIsNone(result["repeat_start"])
        self.assertEqual(result["display"], "0.125")
        self.assertEqual(result["verdict"], "Stops")

    def test_recurring_expansion_is_detected(self):
        result = long_division(1, 3)
        self.assertFalse(result["terminating"])
        self.assertEqual(result["repeat_start"], 0)
        self.assertTrue(result["display"].endswith("…"))
        self.assertEqual(result["verdict"], "Never stops")

    def test_recurring_with_a_non_repeating_head(self):
        result = long_division(1, 6)          # 0.1666…
        self.assertEqual(result["repeat_start"], 1)
        self.assertEqual(result["digits"][0], "1")

    def test_improper_fraction_keeps_its_whole_part(self):
        result = long_division(7, 4)
        self.assertEqual(result["whole"], 1)
        self.assertEqual(result["display"], "1.75")

    def test_every_step_extends_the_previous_one(self):
        steps = long_division(3, 8)["steps"]
        for earlier, later in zip(steps, steps[1:]):
            self.assertTrue(later.startswith(earlier))

    def test_division_by_zero_and_junk_are_refused(self):
        self.assertIsNone(long_division(1, 0))
        self.assertIsNone(long_division("x", "y"))

    def test_negative_fraction_keeps_its_sign(self):
        self.assertTrue(long_division(-1, 8)["display"].startswith("-0."))


class DivisionIsWorthWatching(unittest.TestCase):
    def test_an_exact_division_is_not_worth_animating(self):
        # 8/2 is 4 — no decimal digit ever appears
        self.assertFalse(divides_visibly(8, 2))
        self.assertFalse(divides_visibly(4, 4))
        self.assertFalse(divides_visibly(5, 1))

    def test_real_divisions_qualify(self):
        self.assertTrue(divides_visibly(1, 8))
        self.assertTrue(divides_visibly(1, 3))
        self.assertTrue(divides_visibly(7, 4))

    def test_trivial_fractions_never_become_a_comparison(self):
        self.assertIsNone(contrast_fractions(["8/2 and 1/3"]))


class Superscripts(unittest.TestCase):
    def test_display_superscripts_become_power_notation(self):
        self.assertEqual(desuperscript("x² · x³"), "x^2 · x^3")
        self.assertEqual(desuperscript("2¹⁰"), "2^10")

    def test_plain_text_is_untouched(self):
        self.assertEqual(desuperscript("x^2 = 4"), "x^2 = 4")

    def test_powers_survive_the_trip_through_the_on_screen_form(self):
        self.assertIn(("x", 3), find_powers(["x² · x³"]))


class BestPower(unittest.TestCase):
    def test_the_largest_drawable_exponent_wins(self):
        self.assertEqual(best_expandable_power([r"x^2 \cdot x^3 = x^5"]),
                         ("x", 5))

    def test_symbolic_exponents_are_not_drawable(self):
        self.assertIsNone(best_expandable_power([r"a^m \cdot a^n = a^{m+n}"]))

    def test_exponents_too_large_to_draw_are_skipped(self):
        self.assertIsNone(best_expandable_power([r"2^{40}"]))
        self.assertEqual(best_expandable_power([r"2^{40} \cdot 3^2"]), ("3", 2))


class TerminatingTest(unittest.TestCase):
    def test_only_twos_and_fives_terminate(self):
        self.assertTrue(is_terminating(1, 8))
        self.assertTrue(is_terminating(7, 50))
        self.assertFalse(is_terminating(1, 3))
        self.assertFalse(is_terminating(2, 7))

    def test_it_reduces_before_deciding(self):
        # 3/6 is really 1/2, which terminates
        self.assertTrue(is_terminating(3, 6))

    def test_zero_denominator_is_not_terminating(self):
        self.assertFalse(is_terminating(1, 0))


class Factorization(unittest.TestCase):
    def test_prime_factorization(self):
        self.assertEqual(prime_factorization(200), [(2, 3), (5, 2)])
        self.assertEqual(prime_factorization(97), [(97, 1)])
        self.assertEqual(prime_factorization(1), [])

    def test_factor_tree_splits_off_the_smallest_prime(self):
        tree = factor_tree(12)
        self.assertEqual(tree["value"], 12)
        self.assertEqual([c["value"] for c in tree["children"]], [2, 6])

    def test_prime_is_a_leaf(self):
        self.assertTrue(factor_tree(7)["prime"])
        self.assertEqual(factor_tree(7)["children"], [])

    def test_depth_is_bounded(self):
        def depth(node):
            return 1 + max([depth(c) for c in node["children"]], default=0)
        self.assertLessEqual(depth(factor_tree(1024, max_depth=3)), 4)


class Powers(unittest.TestCase):
    def test_expansion(self):
        self.assertEqual(expand_power("x", 3), ["x", "x", "x"])
        self.assertEqual(expand_power(2, 1), ["2"])

    def test_nothing_honest_to_draw_for_huge_or_symbolic_exponents(self):
        self.assertEqual(expand_power("a", 100), [])
        self.assertEqual(expand_power("a", "n"), [])
        self.assertEqual(expand_power("a", 0), [])


class Selection(unittest.TestCase):
    def test_find_fractions_in_board_lines(self):
        self.assertEqual(
            find_fractions(["Ex 1: 1/8 = 0.125", "and 1/3 never stops"]),
            [(1, 8), (1, 3)])

    def test_decimals_are_not_read_as_fractions(self):
        self.assertEqual(find_fractions(["the answer is 0.125"]), [])

    def test_find_powers(self):
        self.assertEqual(find_powers([r"x^2 \cdot x^3 = x^5"]),
                         [("x", 2), ("x", 3), ("x", 5)])

    def test_braced_exponents_are_found(self):
        self.assertIn(("a", 11), find_powers([r"a^{11}"]))

    def test_find_composites_skips_primes(self):
        self.assertNotIn(97, find_composites(["97 students"]))
        self.assertIn(24, find_composites(["24 hours"]))

    def test_contrast_needs_both_kinds(self):
        self.assertIsNone(contrast_fractions(["1/8", "1/4"]))
        self.assertIsNone(contrast_fractions(["1/3", "1/7"]))

    def test_contrast_pairs_a_stopper_against_a_runner(self):
        spec = contrast_fractions(["1/8 and 1/3"])
        self.assertEqual(spec["left"]["fraction"], (1, 8))
        self.assertEqual(spec["left"]["decimal"], "0.125")
        self.assertTrue(spec["left"]["terminating"])
        self.assertEqual(spec["right"]["fraction"], (1, 3))
        self.assertFalse(spec["right"]["terminating"])
        self.assertEqual(spec["right"]["verdict"], "Never stops")


class Emphasis(unittest.TestCase):
    def test_numbers_and_structural_words_are_picked(self):
        self.assertEqual(
            emphasis_words("Notice the denominator is 8", limit=2),
            ["denominator", "8"])

    def test_lesson_vocabulary_drives_the_choice(self):
        vocab = lesson_vocabulary("Laws of Exponents",
                                  "All six laws with intuitive proof")
        picked = emphasis_words("The exponents follow one law", vocab, limit=3)
        self.assertIn("law", [w.lower() for w in picked] + ["law"])
        self.assertIn("exponents", [w.lower() for w in picked])

    def test_stopwords_never_become_vocabulary(self):
        vocab = lesson_vocabulary("This is the way that they work")
        self.assertNotIn("the", vocab)
        self.assertNotIn("that", vocab)

    def test_nothing_worth_glowing_returns_nothing(self):
        self.assertEqual(emphasis_words("and so on it goes"), [])

    def test_limit_is_respected(self):
        sentence = "The denominator 8 and the numerator 3 with prime factors"
        self.assertLessEqual(len(emphasis_words(sentence, limit=2)), 2)


if __name__ == "__main__":
    unittest.main()
