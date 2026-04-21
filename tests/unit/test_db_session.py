from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.db.session import get_db


def test_get_db_yields_session() -> None:
    mock_session = MagicMock()
    with patch("app.db.session.SessionLocal", return_value=mock_session):
        gen = get_db()
        yielded = next(gen)
        assert yielded is mock_session


def test_get_db_closes_session_on_normal_exit() -> None:
    mock_session = MagicMock()
    with patch("app.db.session.SessionLocal", return_value=mock_session):
        gen = get_db()
        next(gen)
        mock_session.close.assert_not_called()
        with pytest.raises(StopIteration):
            next(gen)
        mock_session.close.assert_called_once()


def test_get_db_closes_session_on_exception() -> None:
    mock_session = MagicMock()
    with patch("app.db.session.SessionLocal", return_value=mock_session):
        gen = get_db()
        next(gen)
        with pytest.raises(RuntimeError):
            gen.throw(RuntimeError("db failure"))
        mock_session.close.assert_called_once()
