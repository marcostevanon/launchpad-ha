import logging
from unittest.mock import MagicMock

import pytest

from ha_launchpad.config.mapping import (
    ALL_PADS,
    ARROW_DOWN_CC,
    ARROW_UP_CC,
    COLOR_LAB_BUTTON_CC,
    COLORS,
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

    lab.handle_cc(ARROW_UP_CC)  # already on the first page
    assert lab.page == 0

    lab.handle_cc(ARROW_DOWN_CC)
    assert lab.page == 1

    lab.handle_cc(ARROW_DOWN_CC)  # no third page to fall into
    assert lab.page == 1

    lab.handle_cc(ARROW_UP_CC)
    assert lab.page == 0


def test_a_scene_button_jumps_straight_to_its_page(lab):
    lab.enter()

    lab.handle_cc(SCENE_COLUMN_CC[1])

    assert lab.page == 1


def test_the_column_shows_which_pages_exist_and_which_is_open(lab):
    lab.enter()
    sent = cc_sent(lab.backend)

    assert sent[SCENE_COLUMN_CC[0]] > sent[SCENE_COLUMN_CC[1]] > 0
    # Six buttons for pages that do not exist, and they stay dark.
    assert all(sent[cc] == 0 for cc in SCENE_COLUMN_CC[PAGE_COUNT:])


def test_at_180_the_column_and_the_arrows_follow_what_the_user_sees():
    """Upside down, the button printed with an up arrow points down, and the
    top of the column is the button the hardware calls the bottom."""
    flipped = ColorLab(MagicMock(), rotation=180)
    flipped.enter()

    flipped.handle_cc(ARROW_UP_CC)
    assert flipped.page == 1  # the arrow the user sees pointing down

    flipped.handle_cc(ARROW_DOWN_CC)
    assert flipped.page == 0

    # First page sits on the button at the user's top of the column, which is
    # the last one in hardware order.
    flipped.handle_cc(SCENE_COLUMN_CC[-2])
    assert flipped.page == 1


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
    assert lab.handle_cc(SCENE_COLUMN_CC[7]) is True


def test_a_closed_lab_claims_nothing(lab):
    assert lab.handle_note(81) is False
    assert lab.handle_cc(ARROW_UP_CC) is False


# --- closing ----------------------------------------------------------------


def test_closing_blanks_everything_the_grid_repaint_cannot_reach(lab):
    lab.enter()
    lab.backend.reset_mock()

    lab.exit()

    assert not lab.active
    cleared = cc_sent(lab.backend)
    assert cleared[COLOR_LAB_BUTTON_CC] == 0
    assert cleared[LOGO_CC] == 0
    assert all(cleared[cc] == 0 for cc in SCENE_COLUMN_CC)


def test_closing_an_already_closed_lab_touches_nothing(lab):
    lab.exit()

    lab.backend.send_cc.assert_not_called()


def test_a_disconnected_board_is_not_painted(lab):
    lab.backend.is_connected.return_value = False

    lab.enter()

    lab.backend.send_velocity.assert_not_called()
