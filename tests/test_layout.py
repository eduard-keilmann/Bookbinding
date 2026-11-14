"""Folding invariants and explicit, independently checked page arrangements."""

import pytest

from bookbinding import make_plan


def test_eight_pages_form_two_nested_sheets():
    signature = make_plan(8, sheets_per_signature=2).signatures[0]
    assert [(side.left, side.right, side.is_back) for side in signature.sides] == [
        (8, 1, False),
        (2, 7, True),
        (6, 3, False),
        (4, 5, True),
    ]


def test_fixed_maximum_and_short_last_signature():
    plan = make_plan(35, sheets_per_signature=4)
    assert [signature.sheet_count for signature in plan.signatures] == [4, 4, 1]
    assert plan.signatures[-1].pages == (33, 34, 35, None)
    assert plan.blank_page_count == 1


def test_custom_signatures_can_add_blank_sheets():
    plan = make_plan(9, signature_sizes=[2, 2])
    assert [signature.sheet_count for signature in plan.signatures] == [2, 2]
    assert plan.signatures[1].pages == (9, None, None, None, None, None, None, None)
    assert plan.blank_page_count == 7


def test_flyleaf_adds_two_pages_at_each_end_before_padding():
    plan = make_plan(3, flyleaf=True)
    assert plan.signatures[0].pages == (None, None, 1, 2, 3, None, None, None)
    assert plan.blank_page_count == 5


@pytest.mark.parametrize("mode", ["signatures", "automatic", "booklet", "perfect-bound"])
@pytest.mark.parametrize("page_count", [1, 3, 4, 8, 17, 64, 65, 192, 193, 197, 1027])
def test_folding_recovers_reading_order_and_every_page_once(mode, page_count):
    plan = make_plan(page_count, mode=mode)
    recovered = []
    for signature in plan.signatures:
        beginning, ending = [], []
        for front, back in zip(signature.sides[::2], signature.sides[1::2], strict=True):
            beginning.extend((front.right, back.left))
            ending[0:0] = [back.right, front.left]
        assert tuple(beginning + ending) == signature.pages
        recovered.extend(beginning + ending)
    assert [page for page in recovered if page is not None] == list(range(1, page_count + 1))
    assert len(recovered) == plan.sheet_count * 4
    assert recovered.count(None) == plan.blank_page_count


@pytest.mark.parametrize("page_count", [0, -1, 1.5, True])
def test_invalid_page_count_is_rejected(page_count):
    with pytest.raises(ValueError, match="mindestens eine Seite"):
        make_plan(page_count)


@pytest.mark.parametrize("sizes", [[], [0], [-2], [1.5], [True], [1]])
def test_invalid_or_insufficient_custom_signatures_are_rejected(sizes):
    with pytest.raises(ValueError):
        make_plan(9, signature_sizes=sizes)


def test_capacity_validation_includes_flyleaves():
    with pytest.raises(ValueError, match="zu klein"):
        make_plan(4, signature_sizes=[1], flyleaf=True)


@pytest.mark.parametrize("size", [0, -1, 1.5, True])
def test_invalid_sheet_maximum_is_rejected(size):
    with pytest.raises(ValueError, match="positive ganze Zahl"):
        make_plan(8, sheets_per_signature=size)


def test_invalid_modes_and_conflicting_options_are_rejected():
    with pytest.raises(ValueError, match="Unbekanntes"):
        make_plan(8, mode="unknown")
    with pytest.raises(ValueError, match="nur im Lagenmodus"):
        make_plan(8, mode="booklet", signature_sizes=[2])
    with pytest.raises(ValueError, match="acht Bögen"):
        make_plan(8, mode="automatic", sheets_per_signature=4)


@pytest.mark.parametrize(
    "page_count, sheets",
    [
        (4, [1]),
        (64, [16]),
        (68, [9, 8]),
        (192, [8, 8, 8, 8, 8, 8]),
        (196, [7, 7, 7, 7, 7, 7, 7]),
        (200, [8, 7, 7, 7, 7, 7, 7]),
        (512, [8] * 16),
        (1024, [8] * 32),
    ],
)
def test_automatic_signature_distribution(page_count, sheets):
    plan = make_plan(page_count, mode="automatic")
    assert [signature.sheet_count for signature in plan.signatures] == sheets
    assert plan.sheet_count == sum(sheets)
    assert plan.blank_page_count == 0
