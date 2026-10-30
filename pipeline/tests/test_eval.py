"""M9 harness: boundary scoring."""

from __future__ import annotations

from tutorialgen.eval import Labels, boundary_scores


def labels(**kw) -> Labels:
    return Labels(video="v", content=[0, 60], boundaries=[10, 20, 30], **kw)


def test_perfect_and_tolerance():
    s = boundary_scores([10.5, 19, 31.5], labels())
    assert s["f1"] == 1.0 and s["mean_abs_error_s"] == 1.0
    assert boundary_scores([13, 20, 30], labels())["recall"] == round(2 / 3, 3)


def test_one_to_one_and_optional_and_edges():
    # Two predictions near one label: only one matches.
    s = boundary_scores([10, 11, 20, 30], labels())
    assert s["true_positives"] == 3 and s["precision"] == 0.75
    # Predictions near optional boundaries and content edges are ignored.
    s = boundary_scores([1, 10, 20, 25, 30, 59], labels(optional_boundaries=[25]))
    assert s["predicted"] == 3 and s["f1"] == 1.0
    assert boundary_scores([], labels())["f1"] == 0.0
