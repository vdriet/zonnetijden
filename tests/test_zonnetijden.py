import datetime

import pytest


@pytest.fixture
def mock_env_weerapikey(monkeypatch):
  monkeypatch.setenv("WEER_API_KEY", "DUMMY")


def test_formatdate(mock_env_weerapikey):
  import zonnetijden

  invoer = datetime.datetime(2024, 12, 7, 19, 2, 37)
  uitvoer = zonnetijden.formatdate(invoer)
  assert uitvoer == '2024-12-07'

def test_formattime(mock_env_weerapikey):
  import zonnetijden

  invoer = datetime.datetime(2024, 12, 7, 19, 2, 37)
  uitvoer = zonnetijden.formattime(invoer)
  assert uitvoer == '19:02'

def test_formattimedelta(mock_env_weerapikey):
  import zonnetijden

  invoer1 = datetime.datetime(2024, 12, 7, 8, 32, 11)
  invoer2 = datetime.datetime(2024, 12, 7, 16, 21, 43)
  uitvoer = zonnetijden.formattimedelta(invoer2 - invoer1)
  assert uitvoer == '7:49:32'
