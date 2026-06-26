from unittest.mock import Mock

import extract


class TestGetDbEngine:
    def test_get_db_engine_builds_mysql_connection_url(self, monkeypatch):
        mock_create_engine = Mock(return_value="fake-engine")
        monkeypatch.setattr(extract.sqlalchemy,
                            "create_engine", mock_create_engine)

        config = {
            "DB_USER": "user",
            "DB_PASSWORD": "pass",
            "DB_HOST": "host",
            "DB_NAME": "dbname",
        }

        engine = extract.get_db_engine(config)

        assert engine == "fake-engine"
        assert mock_create_engine.call_args.args[0] == "mysql+pymysql://user:pass@host/dbname"
