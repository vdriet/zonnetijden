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


def test_formattimeseconds(mock_env_weerapikey):
  import zonnetijden

  invoer = datetime.datetime(2024, 12, 7, 19, 2, 37)
  uitvoer = zonnetijden.formattime(invoer, True)
  assert uitvoer == '19:02:37'


def test_formattimedelta(mock_env_weerapikey):
  import zonnetijden

  invoer1 = datetime.datetime(2024, 12, 7, 8, 32, 11)
  invoer2 = datetime.datetime(2024, 12, 7, 16, 21, 43)
  uitvoer = zonnetijden.formattimedelta(invoer2 - invoer1)
  assert uitvoer == '7:49:32'


def test_berekenzonnetijden():
  import zonnetijden

  verwachting = {'daglengte': '7:38:43', 'datum': '2024-12-21', 'onder': '16:23', 'op': '08:44'}
  resultaat = zonnetijden.getinfohattem('2024-12-21')
  assert resultaat == verwachting


def test_bepaaltoenamekleur():
  import zonnetijden
  assert zonnetijden.bepaaltoenamekleur(0) == 'orangered'
  assert zonnetijden.bepaaltoenamekleur(1) == 'yellow'
  assert zonnetijden.bepaaltoenamekleur(2) == 'gold'
  assert zonnetijden.bepaaltoenamekleur(3) == 'orange'
  assert zonnetijden.bepaaltoenamekleur(4) == 'darkorange'
  assert zonnetijden.bepaaltoenamekleur(5) == 'orangered'


def test_bepaalafnamekleur():
  import zonnetijden
  assert zonnetijden.bepaalafnamekleur(0) == 'royalblue'
  assert zonnetijden.bepaalafnamekleur(-1) == 'lightblue'
  assert zonnetijden.bepaalafnamekleur(-2) == 'lightskyblue'
  assert zonnetijden.bepaalafnamekleur(-3) == 'deepskyblue'
  assert zonnetijden.bepaalafnamekleur(-4) == 'dodgerblue'
  assert zonnetijden.bepaalafnamekleur(-5) == 'royalblue'


def test_bepaalkleur():
  import zonnetijden
  assert zonnetijden.bepaalkleur(1, 1) == 'lawngreen'
  assert zonnetijden.bepaalkleur(0, 1) == 'yellow'
  assert zonnetijden.bepaalkleur(1, 0) == 'lightblue'


def test_bepaalwaterkleur():
  import zonnetijden
  assert zonnetijden.bepaalwaterkleur(0, 1) == ('lightblue', 'dodgerblue')
  assert zonnetijden.bepaalwaterkleur(1, 0) == ('dodgerblue', 'lightblue')
  assert zonnetijden.bepaalwaterkleur(1, 1) == ('dodgerblue', 'lightblue')
