import logging
from unittest.mock import MagicMock

import pytest

from ha_launchpad.config.mapping import (
    ALL_PADS,
    ARROW_DOWN_CC,
    ARROW_UP_CC,
    COLORS,
    FUNCTION_ROW_CC,
    LOGO_CC,
    SCENE_COLUMN_CC,
)
from ha_launchpad.config.palette import PALETTE_HEX, PALETTE_SIZE, describe
from ha_launchpad.features.color_lab import (
    PAGE_COUNT,
    PAGE_PADS,
    PAGE_SIZE,
    ColorLab,
    pad_for_index,
)


@pytest.fixture
def lab():
    return ColorLab(MagicMock(), rotation=0)


def velocities_sent(backend):
    """(pad, velocity) for every swatch written to the grid."""
    return [(c.args[0], c.args[1]) for c in backend.send_velocity.call_args_list]


def cc_sent(backend):
    return {c.args[0]: c.args[1] for c in backend.send_cc.call_args_list}


# --- the palette itself -----------------------------------------------------


def test_the_palette_has_one_entry_per_velocity():
    assert PALETTE_SIZE == 128
    assert all(len(h) == 7 and h.startswith("#") for h in PALETTE_HEX)


def test_every_named_colour_is_a_real_velocity():
    assert all(0 <= velocity < PALETTE_SIZE for velocity in COLORS.values())


def test_describe_names_the_velocities_this_project_uses():
    assert describe(21) == "21 #61FF61 (green_1)"
    # 127 is one of the 87 the project has never named.
    assert describe(127) == "127 #C27661"


def test_describe_does_not_claim_a_colour_for_the_unlit_entry():
    """The manual draws entry 0 as grey so it is visible on a black page."""
    assert describe(0) == "0 unlit (off)"
    assert "#616161" not in describe(0)


# --- layout -----------------------------------------------------------------


def test_the_grid_is_filled_the_way_the_manual_reads():
    assert pad_for_index(0) == 81  # top left
    assert pad_for_index(7) == 88  # end of the first row
    assert pad_for_index(8) == 71  # wraps down, not across
    assert pad_for_index(63) == 18  # bottom right


def test_a_page_covers_the_whole_grid_exactly_once():
    assert len(PAGE_PADS) == PAGE_SIZE
    assert sorted(PAGE_PADS) == sorted(ALL_PADS)


def test_the_pages_cover_the_palette_with_nothing_left_over():
    assert PAGE_COUNT * PAGE_SIZE == PALETTE_SIZE


# --- paging -----------------------------------------------------------------


def test_entering_shows_the_first_half_of_the_palette(lab):
    lab.enter()

    assert lab.active
    assert velocities_sent(lab.backend) == list(zip(PAGE_PADS, range(64)))


def test_the_second_page_shows_the_rest(lab):
    lab.enter()
    lab.backend.reset_mock()

    lab.show_page(1)

    assert velocities_sent(lab.backend) == list(zip(PAGE_PADS, range(64, 128)))


def test_the_arrows_page_through_and_stop_at_the_ends(lab):
    lab.enter()

    lab.handle_cc(lab._previous_page_button)  # already on the first page
    assert lab.page == 0

    lab.handle_cc(lab._next_page_button)
    assert lab.page == 1

    lab.handle_cc(lab._next_page_button)  # no third page to fall into
    assert lab.page == 1

    lab.handle_cc(lab._previous_page_button)
    assert lab.page == 0


def test_an_arrow_lights_only_when_it_leads_somewhere(lab):
    """With two pages, that is also how the board says which one is open."""
    lab.enter()
    on_first = cc_sent(lab.backend)
    assert on_first[lab._previous_page_button] == 0
    assert on_first[lab._next_page_button] > 0

    lab.backend.reset_mock()
    lab.show_page(1)
    on_last = cc_sent(lab.backend)
    assert on_last[lab._previous_page_button] > 0
    assert on_last[lab._next_page_button] == 0


def test_the_way_out_is_never_also_an_arrow():
    """Paging owns the arrows, so the button that closes the lab has to be a
    named one. Chosen by position it would land on an arrow at some rotation,
    and the controller checks it first: paging would stop working entirely."""
    for rotation in (0, 90, 180, 270):
        lab = ColorLab(MagicMock(), rotation=rotation)
        assert lab.toggle_button not in (ARROW_UP_CC, ARROW_DOWN_CC)
        assert lab.toggle_button in FUNCTION_ROW_CC


def test_at_180_the_arrows_follow_what_the_user_sees():
    """Upside down, the button printed with an up arrow points down, and
    reaching page 1 by pressing something that looks like "down" is nonsense."""
    flipped = ColorLab(MagicMock(), rotation=180)
    flipped.enter()

    assert flipped._previous_page_button == ARROW_DOWN_CC
    assert flipped._next_page_button == ARROW_UP_CC

    flipped.handle_cc(ARROW_UP_CC)  # the arrow the user sees pointing down
    assert flipped.page == 1


def test_the_side_column_is_left_alone(lab):
    """It used to carry the page indicator, and nothing does now."""
    lab.enter()

    assert not set(cc_sent(lab.backend)) & set(SCENE_COLUMN_CC)


# --- picking ----------------------------------------------------------------


def test_picking_a_swatch_logs_its_velocity(lab, caplog):
    lab.enter()

    with caplog.at_level(logging.INFO):
        lab.handle_note(PAGE_PADS[21])

    assert "COLOR 21 #61FF61 (green_1)" in caplog.text


def test_the_second_page_logs_the_high_velocities(lab, caplog):
    lab.enter()
    lab.show_page(1)

    with caplog.at_level(logging.INFO):
        lab.handle_note(PAGE_PADS[0])

    assert "COLOR 64 " in caplog.text


def test_the_pick_is_echoed_on_the_logo(lab):
    lab.enter()
    lab.backend.reset_mock()

    lab.handle_note(PAGE_PADS[45])

    lab.backend.send_cc.assert_called_once_with(LOGO_CC, 45)


def test_presses_are_swallowed_so_nothing_reaches_home_assistant(lab):
    lab.enter()

    assert lab.handle_note(PAGE_PADS[0]) is True
    # A button around the grid that the lab has no use for is still consumed.
    assert lab.handle_cc(SCENE_COLUMN_CC[7]) is True


def test_a_closed_lab_claims_nothing(lab):
    assert lab.handle_note(81) is False
    assert lab.handle_cc(FUNCTION_ROW_CC[1]) is False


# --- closing ----------------------------------------------------------------


def test_closing_blanks_everything_the_grid_repaint_cannot_reach(lab):
    lab.enter()
    lab.backend.reset_mock()

    lab.exit()

    assert not lab.active
    cleared = cc_sent(lab.backend)
    assert cleared[lab.toggle_button] == 0
    assert cleared[LOGO_CC] == 0
    assert cleared[lab._previous_page_button] == 0
    assert cleared[lab._next_page_button] == 0


def test_closing_an_already_closed_lab_touches_nothing(lab):
    lab.exit()

    lab.backend.send_cc.assert_not_called()


def test_a_disconnected_board_is_not_painted(lab):
    lab.backend.is_connected.return_value = False

    lab.enter()

    lab.backend.send_velocity.assert_not_called()
