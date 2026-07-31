import logging
from unittest.mock import MagicMock

import pytest

from ha_launchpad.config.mapping import (
    ALL_PADS,
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


def test_a_page_button_jumps_straight_to_its_page(lab):
    lab.enter()

    lab.handle_cc(lab._page_buttons[1])
    assert lab.page == 1

    lab.handle_cc(lab._page_buttons[0])
    assert lab.page == 0


def test_the_page_buttons_show_which_one_is_open(lab):
    lab.enter()
    sent = cc_sent(lab.backend)

    assert sent[lab._page_buttons[0]] > sent[lab._page_buttons[1]] > 0


def test_the_controls_sit_together_next_to_the_way_out(lab):
    """One corner, one cluster: exit, then a button per page beside it."""
    assert lab.toggle_button == FUNCTION_ROW_CC[0]
    assert lab._page_buttons == FUNCTION_ROW_CC[1:3]
    assert len(lab._page_buttons) == PAGE_COUNT


def test_at_180_the_cluster_follows_the_user_to_the_other_end_of_the_row():
    """Upside down, the corner the user calls left is the case's right end."""
    flipped = ColorLab(MagicMock(), rotation=180)

    assert flipped.toggle_button == FUNCTION_ROW_CC[-1]
    assert flipped._page_buttons == FUNCTION_ROW_CC[-2:-4:-1]

    flipped.enter()
    flipped.handle_cc(flipped._page_buttons[1])
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
    assert all(cleared[cc] == 0 for cc in lab._page_buttons)


def test_closing_an_already_closed_lab_touches_nothing(lab):
    lab.exit()

    lab.backend.send_cc.assert_not_called()


def test_a_disconnected_board_is_not_painted(lab):
    lab.backend.is_connected.return_value = False

    lab.enter()

    lab.backend.send_velocity.assert_not_called()
