import json
import logging

import pytest

from devworkwire.shared import log_config


@pytest.fixture(autouse=True)
def restore_root_logger():
    """Snapshot and restore global root-logger state mutated by these tests."""
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)
    log_config.clear_context()


def make_record(msg: str = "hello %s", args=("world",)) -> logging.LogRecord:
    return logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=args,
        exc_info=None,
    )


class TestJsonFormatter:
    def test_emits_single_line_json(self):
        formatter = log_config._JsonFormatter()

        line = formatter.format(make_record())

        assert "\n" not in line
        payload = json.loads(line)
        assert payload["level"] == "INFO"
        assert payload["logger"] == "test.logger"
        assert payload["message"] == "hello world"
        assert "timestamp" in payload

    def test_correlation_ids_default_to_placeholder(self):
        formatter = log_config._JsonFormatter()

        payload = json.loads(formatter.format(make_record()))

        assert payload["request_id"] == "-"
        assert payload["user_id"] == "-"

    def test_extra_fields_are_surfaced(self):
        record = make_record()
        setattr(record, "issue_key", "OPH-1")

        payload = json.loads(log_config._JsonFormatter().format(record))

        assert payload["issue_key"] == "OPH-1"

    def test_reserved_attributes_are_not_leaked_as_extras(self):
        record = make_record()

        payload = json.loads(log_config._JsonFormatter().format(record))

        assert set(payload.keys()) == {
            "timestamp",
            "level",
            "logger",
            "request_id",
            "user_id",
            "message",
        }


class TestPlainFormatter:
    def test_contains_level_and_message(self):
        line = log_config._PlainFormatter().format(make_record())

        assert "INFO" in line
        assert "hello world" in line
        assert "\n" not in line

    def test_colored_mode_wraps_level_in_ansi(self):
        line = log_config._PlainFormatter(colored=True).format(make_record())

        assert log_config._COLORS["INFO"] in line
        assert log_config._RESET in line


class TestCorrelationContext:
    def test_context_filter_injects_ids_into_records(self):
        log_config.set_request_id("req-1")
        log_config.set_user_id("user-9")
        context_filter = log_config._ContextFilter()
        record = make_record()

        assert context_filter.filter(record) is True
        assert record.request_id == "req-1"
        assert record.user_id == "user-9"

    def test_clear_context_resets_ids(self):
        log_config.set_request_id("req-1")
        log_config.clear_context()
        record = make_record()

        log_config._ContextFilter().filter(record)

        assert record.request_id == "-"
        assert record.user_id == "-"


class TestInitializeLogging:
    def test_text_format_installs_plain_formatter_and_level(self):
        log_config.initialize_logging(level="DEBUG", format_type="text")
        root = logging.getLogger()

        assert root.level == logging.DEBUG
        assert isinstance(root.handlers[0].formatter, log_config._PlainFormatter)

    def test_json_format_is_the_default_formatter(self):
        log_config.initialize_logging(level="INFO")

        assert isinstance(
            logging.getLogger().handlers[0].formatter, log_config._JsonFormatter
        )

    def test_console_disabled_removes_handlers(self):
        log_config.initialize_logging(console_enabled=False)

        assert logging.getLogger().handlers == []
