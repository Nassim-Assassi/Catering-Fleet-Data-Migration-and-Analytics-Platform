from unittest.mock import Mock

import logging
import logging_config


class TestGetLogger:
    def test_get_logger_returns_namespaced_logger(self):
        logger = logging_config.get_logger("unit.test.logger")

        assert logger.name == "unit.test.logger"


class TestConfigureLogging:
    def test_configure_logging_uses_debug_level_when_verbose(self, monkeypatch):
        mock_basic_config = Mock()
        monkeypatch.setattr(logging_config.logging,
                            "basicConfig", mock_basic_config)

        logging_config.configure_logging(verbose=True)

        kwargs = mock_basic_config.call_args.kwargs
        assert kwargs["level"] == logging.DEBUG

    def test_configure_logging_uses_info_level_by_default(self, monkeypatch):
        mock_basic_config = Mock()
        monkeypatch.setattr(logging_config.logging,
                            "basicConfig", mock_basic_config)

        logging_config.configure_logging()

        kwargs = mock_basic_config.call_args.kwargs
        assert kwargs["level"] == logging.INFO
