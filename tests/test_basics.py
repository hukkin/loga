import logging
import os
import sys
from typing import Any, Mapping
from unittest.mock import ANY, Mock, call, mock_open, patch

import pytest

from loga import Loga

test_setup: Mapping[str, Any] = {
    "do_write": True,
    "log_if_graylog_disabled": False,
    "private_data": {"mnemonic", "priv"},
}

loga = Loga(**test_setup)


@loga
def function_with_private_arg(priv, acceptable=True):
    return acceptable


@loga
def function_with_private_kwarg(number, a_float=0.0, mnemonic=None):
    return number * a_float


# we can also use loga.__call__
@loga
def may_or_may_not_error_test(first, other, kwargs=None):
    """A function that may or may not error."""
    if not kwargs:
        raise ValueError("no good")
    else:
        return (first + other, kwargs)


@loga
def aaa():
    return "this"


@loga
class AllMethodTypes:
    def __secret__(self):
        """a method that should never be logged."""
        return True

    def public(self):
        """normal method."""
        return True

    @classmethod
    def cl(cls):
        """class method."""
        return True

    @staticmethod
    def st():
        """static method."""
        return True

    @loga
    def doubled(self):
        """Loga twice, bad but shouldn't kill."""
        return True


all_method_types = AllMethodTypes()


class NoRepr:
    """An object that really hates being repr'd."""

    def __repr__(self):
        raise Exception("No.")


@loga
class DummyClass:
    """A class with regular methods, static methods and errors."""

    non_callable = False

    def add(self, a, b):
        return a + b

    def add_and_maybe_subtract(self, a, b, c=False):
        added = a + b
        if c:
            return added - c
        return added

    @staticmethod
    def static_method(number):
        return number * number

    def optional_provided(self, kw=None, **kwargs):
        if kw:
            raise ValueError("Should not have provided!")

    @loga.ignore
    def hopefully_ignored(self, n):
        return n**n

    @loga.errors
    def hopefully_only_errors(self, n):
        raise ValueError("Bam!")


class DummyClass2:
    def add(self, a, b, c):
        return a + b + c


@loga.errors
class ForErrors:
    def one(self):
        raise ValueError("Boom!")

    def two(self):
        return True


@loga.errors
def first_test_func(number):
    raise ValueError("Broken!")


within = {"lst": [], "ok": {"ok": {"priv": "secret"}}}
beyond = {"lst": [], "ok": {"ok": {"ok": {"ok": {"ok": {"ok": {"priv": "allowed"}}}}}}}


@loga
def func_with_recursive_data_beyond(data):
    pass


@loga
def func_with_recursive_data_within(data):
    pass


dummy = DummyClass()


class TestDecoration:
    def test_inheritance_signature_change(self):
        d2 = DummyClass2()
        assert 6 == d2.add(1, 2, 3)

    def test_errors_on_func(self):
        with patch("logging.Logger.log") as logger:
            with pytest.raises(ValueError):
                first_test_func(5)
            (alert, logged_msg), extras = logger.call_args_list[-1]
            expected_msg = '*Errored during first_test_func(number=5) with ValueError "Broken!"'
            assert logged_msg == expected_msg

    def test_one(self):
        """Check that an error is thrown for a func."""
        with patch("logging.Logger.log") as logger:
            with pytest.raises(ValueError, match="no good"):
                may_or_may_not_error_test("astadh", 1331)
            (alert, logged_msg), extras = logger.call_args
            assert alert == 10
            expected_msg = (
                "*Errored during may_or_may_not_error_test(first='astadh', "
                'other=1331) with ValueError "no good"'
            )
            assert logged_msg == expected_msg

    def test_logme_0(self):
        """Test correct result."""
        with patch("logging.Logger.log") as logger:
            res, kwa = may_or_may_not_error_test(2534, 2466, kwargs=True)
            assert res == 5000
            assert kwa
            (alert, logged_msg), extras = logger.call_args_list[0]
            expected_msg = "*Called may_or_may_not_error_test(first=2534, other=2466, kwargs=True)"
            assert logged_msg == expected_msg
            (alert, logged_msg), extras = logger.call_args_list[-1]
            expected_msg = (
                "*Returned from may_or_may_not_error_test(first=2534, other=2466, "
                "kwargs=True) with tuple ((5000, True))"
            )
            assert logged_msg == expected_msg

    def test_logme_1(self):
        with patch("logging.Logger.log") as logger:
            result = dummy.add(1, 2)
            assert result == 3
            (alert, logged_msg), extras = logger.call_args_list[0]
            assert logged_msg == "*Called DummyClass.add(a=1, b=2)"
            (alert, logged_msg), extras = logger.call_args_list[-1]
            assert "*Returned from DummyClass.add(a=1, b=2) with int (3)" == logged_msg

    def test_everything_0(self):
        with patch("logging.Logger.log") as logger:
            dummy.add_and_maybe_subtract(15, 10, 5)
            (alert, logged_msg), extras = logger.call_args_list[0]
            expected_msg = "*Called DummyClass.add_and_maybe_subtract(a=15, b=10, c=5)"
            assert logged_msg == expected_msg
            (alert, logged_msg), extras = logger.call_args_list[-1]
            expected_msg = "*Returned from DummyClass.add_and_maybe_subtract(a=15, b=10, c=5) with int (20)"  # noqa: E501
            assert expected_msg == logged_msg

    def test_everything_1(self):
        with patch("logging.Logger.log") as logger:
            result = dummy.static_method(10)
            assert result == 100
            (alert, logged_msg), extras = logger.call_args_list[-1]
            expected_msg = "*Returned from DummyClass.static_method(number=10) with int (100)"
            assert logged_msg == expected_msg

    def test_everything_3(self):
        with patch("logging.Logger.log") as logger:
            dummy.optional_provided()
            (alert, logged_msg), extras = logger.call_args_list[0]
            assert logged_msg == "*Called DummyClass.optional_provided()"
            (alert, logged_msg), extras = logger.call_args_list[-1]
            assert "Returned None" in logged_msg

    def test_everything_4(self):
        with patch("logging.Logger.log") as logger:
            with pytest.raises(ValueError, match="Should not have provided!"):
                result = dummy.optional_provided(kw="Something")
                assert result is None
                (alert, logged_msg), extras = logger.call_args_list[0]
                assert "0 args, 1 kwargs" in logged_msg
                (alert, logged_msg), extras = logger.call_args_list[-1]
                assert "Errored with ValueError" in logged_msg, logged_msg

    def test_loga_ignore(self):
        with patch("logging.Logger.log") as logger:
            result = dummy.hopefully_ignored(5)
            assert result == 5**5
            logger.assert_not_called()

    def test_loga_errors(self):
        with patch("logging.Logger.log") as logger:
            with pytest.raises(ValueError):
                dummy.hopefully_only_errors(5)
            (alert, logged_msg), extras = logger.call_args
            expected_msg = '*Errored during DummyClass.hopefully_only_errors(n=5) with ValueError "Bam!"'  # noqa: E501
            assert expected_msg == logged_msg

    def test_error_deco(self):
        """Test that @loga.errors logs only errors when decorating a class."""
        with patch("logging.Logger.log") as logger:
            fe = ForErrors()
            assert fe.two()
            logger.assert_not_called()
            with pytest.raises(ValueError):
                fe.one()
            assert logger.call_count == 1
            (alert, logged_msg), extras = logger.call_args
            assert logged_msg == '*Errored during ForErrors.one() with ValueError "Boom!"'

    def test_private_keyword_removal(self):
        with patch("logging.Logger.log") as logger:
            mnem = "every good boy deserves fruit"
            res = function_with_private_kwarg(10, a_float=5.5, mnemonic=mnem)
            assert res == 10 * 5.5
            (_alert, _logged_msg), extras = logger.call_args_list[0]
            assert extras["extra"]["mnemonic"] == "'********'"

    def test_private_positional_removal(self):
        with patch("logging.Logger.log") as logger:
            res = function_with_private_arg("should not log", False)
            assert not res
            (_alert, _logged_msg), extras = logger.call_args_list[0]
            assert extras["extra"]["priv"] == "'********'"

    def test_private_beyond(self):
        with patch("logging.Logger.log") as logger:
            func_with_recursive_data_beyond(beyond)
            (_alert, _logged_msg), extras = logger.call_args_list[0]
            assert "allowed" in extras["extra"]["data"]

    def test_private_within(self):
        with patch("logging.Logger.log") as logger:
            func_with_recursive_data_within(within)
            (_alert, _logged_msg), extras = logger.call_args_list[0]
            assert "secret" not in extras["extra"]["data"]


class TestLog:
    def setup_method(self):
        self.logfile = "./logs/logs.txt"
        self.log_msg = "This is a message that can be used when the content does not matter."
        self.log_data = {
            "This is": "log data",
            "that can be": "used when content does not matter",
        }
        self.loga = Loga(
            do_print=True,
            do_write=True,
            logfile=self.logfile,
            log_if_graylog_disabled=False,
        )
        self.log = self.loga.log

    def test_protected_keys(self):
        """Test that protected log data keys are renamed.

        Check that a protected name "name" is converted to
        "protected_name", in order to stop error in logger later.
        """
        with patch("logging.Logger.log") as mock_log:
            self.log(logging.INFO, "fine", {"name": "bad", "other": "good"})
            (_alert, _msg), kwargs = mock_log.call_args
            assert kwargs["extra"]["protected_name"] == "bad"
            assert kwargs["extra"]["other"] == "good"

    def test_can_log(self):
        with patch("logging.Logger.log") as logger:
            level_num = 50
            msg = "Test message here"
            result = self.log(level_num, msg, {"extra": "data"})
            assert result is None
            (alert, logged_msg), extras = logger.call_args
            assert alert == level_num
            assert msg == logged_msg
            assert extras["extra"]["extra"] == "data"

    def test_write_to_file(self):
        """Check that we can write logs to file."""
        open_ = mock_open()
        with patch("builtins.open", open_):
            loga = Loga(
                do_write=True,
                logfile=self.logfile,
                log_if_graylog_disabled=False,
            )
            loga.log(logging.INFO, "An entry in our log")

        expected_logfile = os.path.abspath(os.path.expanduser(self.logfile))
        if sys.version_info < (3, 9):
            expected_open_call = call(expected_logfile, "a", encoding=None)
        elif sys.version_info < (3, 10):
            expected_open_call = call(expected_logfile, "a", encoding=None, errors=None)
        else:
            expected_open_call = call(expected_logfile, "a", encoding="locale", errors=None)
        open_.assert_has_calls([expected_open_call])
        open_().write.assert_called()

    def test_int_truncation(self):
        """Test that large ints in log data are truncated."""
        truncation = 100
        loga = Loga(truncation=truncation)
        msg = "This is simply a test of the int truncation inside the log."
        large_number = 10 ** (truncation + 1)
        log_data = {"key": large_number}
        with patch("logging.Logger.log") as mock_log:
            loga.log(logging.INFO, msg, log_data)
        mock_log.assert_called_with(20, msg, extra=ANY)
        logger_was_passed = mock_log.call_args[1]["extra"]["key"]
        truncation_suffix = "..."
        done_by_hand = str(large_number)[: truncation - len(truncation_suffix)] + truncation_suffix
        assert logger_was_passed == done_by_hand

    def test_string_truncation_fail(self):
        """If something cannot be cast to string, we need to know about it."""
        with patch("logging.Logger.log") as mock_log:
            no_string_rep = NoRepr()
            result = self.loga._force_string_and_truncate(no_string_rep, 7500)
            assert result == "<<Unstringable input>>"
            (alert, msg), kwargs = mock_log.call_args
            assert "Object could not be cast to string" == msg

    def test_msg_truncation(self):
        """Test log message truncation."""
        default_truncation_len = 7500
        truncation_suffix = "..."
        with patch("logging.Logger.log") as mock_log:
            self.loga.info("a" * 50000)
            mock_log.assert_called_with(
                logging.INFO,
                "a" * (default_truncation_len - len(truncation_suffix)) + truncation_suffix,
                extra=ANY,
            )

    def test_trace_truncation(self):
        """Test that trace is truncated correctly."""
        trace_truncation = 100
        loga = Loga(trace_truncation=trace_truncation)
        for trace_key in {"trace", "traceback"}:
            msg = "This is simply a test of the int truncation inside the log."
            large_number = 10 ** (trace_truncation + 1)
            log_data = {trace_key: large_number}
            with patch("logging.Logger.log") as mock_log:
                loga.log(logging.INFO, msg, log_data)
            mock_log.assert_called_with(20, msg, extra=ANY)
            logger_was_passed = mock_log.call_args[1]["extra"][trace_key]
            truncation_suffix = "..."
            done_by_hand = (
                str(large_number)[: trace_truncation - len(truncation_suffix)] + truncation_suffix
            )
            assert logger_was_passed == done_by_hand

    def test_fail_to_add_entry(self):
        with patch("logging.Logger.log") as mock_log:
            no_string_rep = NoRepr()
            sample = {"fine": 123, "not_fine": no_string_rep}
            result = self.loga.sanitise(sample)
            (alert, msg), kwargs = mock_log.call_args
            assert "Object could not be cast to string" == msg
            assert result["not_fine"] == "<<Unstringable input>>"
            assert result["fine"] == "123"

    def test_log_fail(self):
        with patch("logging.Logger.log") as mock_log:
            mock_log.side_effect = Exception("Really dead.")
            with pytest.raises(Exception):
                self.loga.log(logging.INFO, "Anything")

    def test_loga_pause(self):
        with patch("logging.Logger.log") as mock_log:
            with loga.pause():
                loga.log(logging.INFO, "test")
            mock_log.assert_not_called()
            loga.log(logging.INFO, "test")
            mock_log.assert_called()

    def test_loga_pause_error(self):
        with patch("logging.Logger.log") as logger:
            with loga.pause():
                with pytest.raises(ValueError):
                    may_or_may_not_error_test("one", "two")
            (alert, msg), kwargs = logger.call_args
            expected_msg = (
                "*Errored during may_or_may_not_error_test(first='one', "
                "other='two') with ValueError \"no good\""
            )
            assert expected_msg == msg
            logger.assert_called_once()
            logger.reset()
            with pytest.raises(ValueError):
                may_or_may_not_error_test("one", "two")
                assert len(logger.call_args_list) == 2

    def test_loga_error_suppressed(self):
        with patch("logging.Logger.log") as logger:
            with loga.pause(allow_errors=False):
                with pytest.raises(ValueError):
                    may_or_may_not_error_test("one", "two")
            logger.assert_not_called()
            loga.log(logging.INFO, "test")
            logger.assert_called_once()

    def test_see_below(self):
        """legacy test, deletable if it causes problems later."""
        with patch("logging.Logger.log") as logger:
            loga.log(50, "test")
            (alert, msg), kwargs = logger.call_args
            assert "-- see below:" not in msg

    def test_compat(self):
        test = "a string"
        with patch("loga.Loga.log") as logger:
            loga.log(logging.INFO, test, {})
        args = logger.call_args
        assert isinstance(args[0][0], int)
        assert args[0][1] == test
        assert args[0][2] == {}
        with patch("logging.Logger.log") as logger:
            loga.log(logging.INFO, test)
        (alert, msg), kwargs = logger.call_args
        assert test == msg

    def test_bad_args(self):
        @loga
        def dummy(needed):
            return needed

        with pytest.raises(TypeError):
            dummy()

    def _working_normally(self):
        with patch("logging.Logger.log") as logger:
            res = aaa()
            assert res == "this"
            assert logger.call_count == 2
            (alert, logged_msg), extras = logger.call_args_list[0]
            assert logged_msg.startswith("*Called")
            (alert, logged_msg), extras = logger.call_args_list[-1]
            assert logged_msg.startswith("*Returned")

    def _not_logging(self):
        with patch("logging.Logger.log") as logger:
            res = aaa()
            assert res == "this"
            logger.assert_not_called()

    def test_stop_and_start(self):
        """Check that the start and stop commands actually do something."""
        loga.start()
        self._working_normally()
        loga.stop()
        self._not_logging()
        loga.start()
        self._working_normally()

    def test_debug(self):
        with patch("loga.Loga.log") as logger:
            self.loga.debug(self.log_msg, self.log_data)
            logger.assert_called_with(logging.DEBUG, self.log_msg, extra=self.log_data, safe=False)

    def test_info(self):
        with patch("loga.Loga.log") as logger:
            self.loga.info(self.log_msg, self.log_data)
            logger.assert_called_with(logging.INFO, self.log_msg, extra=self.log_data, safe=False)

    def test_warning(self):
        with patch("loga.Loga.log") as logger:
            self.loga.warning(self.log_msg, self.log_data)
            logger.assert_called_with(
                logging.WARNING, self.log_msg, extra=self.log_data, safe=False
            )

    def test_error(self):
        with patch("loga.Loga.log") as logger:
            self.loga.error(self.log_msg, self.log_data)
            logger.assert_called_with(logging.ERROR, self.log_msg, extra=self.log_data, safe=False)

    def test_critical(self):
        with patch("loga.Loga.log") as logger:
            self.loga.critical(self.log_msg, self.log_data)
            logger.assert_called_with(
                logging.CRITICAL, self.log_msg, extra=self.log_data, safe=False
            )

    def test_listen_to(self):
        sub_loga_facility = "a sub logger"
        sub_loga = Loga(facility=sub_loga_facility)
        self.loga.listen_to(sub_loga_facility)
        self.loga.log = Mock()  # type: ignore[assignment]
        warn = "The parent logger should log this message after sublogger logs it"
        sub_loga.log(logging.WARNING, warn)
        self.loga.log.assert_called_with(logging.WARNING, warn, ANY)
