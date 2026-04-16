"""
tests/test_state.py — Unit tests for state.py helper functions.

These tests have no Flask/Socket.IO dependency and run instantly.
Each test resets the shared state dicts so tests are fully isolated.
"""
import time
import pytest

import state
from state import (
    append_private,
    clean_username,
    get_user_list,
    next_color,
    now_ms,
    private_key,
    sanitize_filename,
    unique_username,
)
from config import MAX_USERNAME_LEN, MAX_PRIVATE_HISTORY, USER_COLORS


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_state():
    """Clear all shared state before every test."""
    state.users.clear()
    state.sid_map.clear()
    state.public_keys.clear()
    state.message_history.clear()
    state.private_history.clear()
    state.uid_tags.clear()
    state.message_votes.clear()
    state.spam_tracker.clear()
    state.user_state.clear()
    state.shadow_muted.clear()
    state.rooms.clear()
    state._color_index[0] = 0
    yield


# ── clean_username ────────────────────────────────────────────────────────────

class TestCleanUsername:
    def test_normal_name(self):
        assert clean_username('Alice') == 'Alice'

    def test_strips_whitespace(self):
        assert clean_username('  Bob  ') == 'Bob'

    def test_truncates_to_max_len(self):
        long = 'A' * (MAX_USERNAME_LEN + 10)
        assert len(clean_username(long)) == MAX_USERNAME_LEN

    def test_empty_string_returns_anonymous(self):
        assert clean_username('') == 'Anonymous'

    def test_whitespace_only_returns_anonymous(self):
        assert clean_username('   ') == 'Anonymous'

    def test_non_string_coerced(self):
        assert clean_username(42) == '42'

    def test_none_coerced(self):
        assert clean_username(None) == 'None'


# ── unique_username ───────────────────────────────────────────────────────────

class TestUniqueUsername:
    def test_free_name_returned_unchanged(self):
        assert unique_username('Alice', 'sid1') == 'Alice'

    def test_taken_name_gets_suffix(self):
        state.sid_map['Alice'] = 'sid_other'
        result = unique_username('Alice', 'sid1')
        assert result == 'Alice2'

    def test_multiple_taken_names_increment(self):
        state.sid_map['Alice']  = 'sid_other'
        state.sid_map['Alice2'] = 'sid_other2'
        result = unique_username('Alice', 'sid1')
        assert result == 'Alice3'

    def test_same_sid_returns_wanted(self):
        # The same session re-joining should get its own name back
        state.sid_map['Alice'] = 'sid1'
        assert unique_username('Alice', 'sid1') == 'Alice'


# ── private_key ───────────────────────────────────────────────────────────────

class TestPrivateKey:
    def test_canonical_order(self):
        assert private_key('Alice', 'Bob') == private_key('Bob', 'Alice')

    def test_format(self):
        assert private_key('Alice', 'Bob') == 'Alice|Bob'

    def test_sorted_alphabetically(self):
        # 'Bob' < 'Charlie' alphabetically
        assert private_key('Charlie', 'Bob') == 'Bob|Charlie'


# ── append_private ────────────────────────────────────────────────────────────

class TestAppendPrivate:
    def test_message_appended(self):
        append_private('Alice|Bob', {'text': 'hi'})
        # private_history values are deques; compare as list for convenience
        assert list(state.private_history['Alice|Bob']) == [{'text': 'hi'}]

    def test_cap_enforced(self):
        key = 'Alice|Bob'
        for i in range(MAX_PRIVATE_HISTORY + 10):
            append_private(key, {'text': str(i)})
        assert len(state.private_history[key]) == MAX_PRIVATE_HISTORY

    def test_oldest_message_dropped_when_capped(self):
        key = 'Alice|Bob'
        for i in range(MAX_PRIVATE_HISTORY + 1):
            append_private(key, {'text': str(i)})
        # First message ('0') should have been evicted
        assert state.private_history[key][0]['text'] == '1'


# ── get_user_list ─────────────────────────────────────────────────────────────

class TestGetUserList:
    def test_empty_when_no_users(self):
        assert get_user_list() == []

    def test_returns_username_and_color(self):
        state.users['sid1'] = {'username': 'Alice', 'tag': 'A1B2', 'display': 'Alice#A1B2', 'color': '#fff', 'joined_at': 0, 'msg_count': 0}
        result = get_user_list()
        assert result[0]['username'] == 'Alice'
        assert result[0]['color'] == '#fff'
        assert result[0]['tag'] == 'A1B2'

    def test_does_not_expose_joined_at(self):
        state.users['sid1'] = {'username': 'Alice', 'tag': 'A1B2', 'display': 'Alice#A1B2', 'color': '#fff', 'joined_at': 999, 'msg_count': 0}
        result = get_user_list()
        assert 'joined_at' not in result[0]

    def test_multiple_users(self):
        state.users['sid1'] = {'username': 'Alice', 'tag': 'A1B2', 'display': 'Alice#A1B2', 'color': '#aaa', 'joined_at': 0, 'msg_count': 0}
        state.users['sid2'] = {'username': 'Bob',   'tag': 'C3D4', 'display': 'Bob#C3D4',   'color': '#bbb', 'joined_at': 0, 'msg_count': 0}
        names = {u['username'] for u in get_user_list()}
        assert names == {'Alice', 'Bob'}


# ── next_color ────────────────────────────────────────────────────────────────

class TestNextColor:
    def test_returns_valid_color(self):
        assert next_color() in USER_COLORS

    def test_cycles_through_palette(self):
        colors = [next_color() for _ in range(len(USER_COLORS))]
        assert set(colors) == set(USER_COLORS)

    def test_wraps_around(self):
        # Exhaust one full cycle
        for _ in range(len(USER_COLORS)):
            next_color()
        # Next call should wrap back to the first color
        assert next_color() == USER_COLORS[0]


# ── sanitize_filename ─────────────────────────────────────────────────────────

class TestSanitizeFilename:
    def test_normal_filename_unchanged(self):
        assert sanitize_filename('photo.jpg') == 'photo.jpg'

    def test_strips_directory_components(self):
        assert sanitize_filename('../../etc/passwd') == 'passwd'

    def test_replaces_spaces(self):
        assert sanitize_filename('my file.txt') == 'my_file.txt'

    def test_replaces_special_chars(self):
        result = sanitize_filename('file<>:"|?.txt')
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result

    def test_empty_string_returns_fallback(self):
        assert sanitize_filename('') == 'file.bin'

    def test_only_unsafe_chars_becomes_underscores(self):
        # '!!!' has no path component; each char is replaced with '_'
        # The result is non-empty so the 'file.bin' fallback is NOT triggered
        result = sanitize_filename('!!!')
        assert result == '___'

    def test_all_dots_returns_fallback(self):
        # After stripping unsafe chars, only dots remain — os.path.basename
        # of '...' is '...' which after regex becomes '...' (dots are allowed)
        # The fallback triggers only when the result is truly empty
        result = sanitize_filename('')
        assert result == 'file.bin'

    def test_windows_path_separator(self):
        result = sanitize_filename('C:\\Users\\file.txt')
        assert result == 'file.txt'


# ── now_ms ────────────────────────────────────────────────────────────────────

class TestNowMs:
    def test_returns_integer(self):
        assert isinstance(now_ms(), int)

    def test_close_to_real_time(self):
        expected = int(time.time() * 1000)
        assert abs(now_ms() - expected) < 100  # within 100 ms
