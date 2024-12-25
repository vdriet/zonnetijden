import json
from unittest.mock import patch
from freezegun import freeze_time

import pytest
from flask import Flask


@pytest.fixture
def mock_env_weerapikey(monkeypatch):
  monkeypatch.setenv("WEER_API_KEY", "DUMMY")


@pytest.fixture()
def app():
  app = Flask(__name__, template_folder="../templates")
  app.config.update({
    "TESTING": True,
  })

  @app.route('/vandaag', methods=['GET'])
  def vandaag():
    import zonnetijden
    return zonnetijden.vandaagget()

  @app.route('/weer', methods=['GET'])
  def weer():
    import zonnetijden
    return zonnetijden.weerget()

  @app.route('/zon', methods=['GET'])
  def zon():
    import zonnetijden
    return zonnetijden.zonget()

  yield app


@pytest.fixture()
def client(app):
  return app.test_client()


@pytest.fixture()
def clear_cache():
  import zonnetijden
  yield
  zonnetijden.getwaterinfo.cache_clear()


@freeze_time("2024-12-23 13:28:00")
def test_vandaag(mock_env_weerapikey, client):
  response = client.get('/vandaag')
  assert b'<title>Vandaag in Hattem</title>' in response.data
  assert b'<td>2024-11-25</td>' in response.data
  assert b'<td>2024-12-16</td>' in response.data
  assert b'<td>2024-12-23</td>' in response.data
  assert b'<td>2024-12-30</td>' in response.data
  assert b'<td>2025-01-20</td>' in response.data
  assert b'<td>2025-01-19</td>' not in response.data


def readjsonfromfile():
  f = open('tests/testdata_weerinfo.json', 'r')
  return json.loads(f.read())


@patch('zonnetijden.getweerinfo')
@patch('waterstand.haalwaterstand', return_value={'resultaat': 'OK', 'tijd': '23-11 16:50', 'nu': 84.0, 'morgen': 89.0})
@freeze_time("2024-11-23 13:50:00")
def test_weer_voor15(mock_waterstand, mock_getweerinfo, mock_env_weerapikey, clear_cache, client):
  testdata = readjsonfromfile()

  mock_getweerinfo.return_value = testdata

  response = client.get('/weer')
  assert b'<title>Vandaag in Hattem</title>' in response.data
  assert b'<div class="temperatuur">3.6</div>' in response.data
  assert b'<div class="waterstand">84 - 89</div>' in response.data
  assert b'<div class="verw0">3 / 3</div>' in response.data
  assert b'<div class="verw1">3 / 6</div>' in response.data
  assert mock_waterstand.called

@patch('zonnetijden.getweerinfo')
@patch('waterstand.haalwaterstand', return_value={'resultaat': 'OK', 'tijd': '23-11 16:50', 'nu': 84.0, 'morgen': 89.0})
@freeze_time("2024-11-23 16:50:00")
def test_weer_na15(mock_waterstand, mock_getweerinfo, mock_env_weerapikey, clear_cache, client):
  testdata = readjsonfromfile()

  mock_getweerinfo.return_value = testdata

  response = client.get('/weer')
  assert b'<title>Vandaag in Hattem</title>' in response.data
  assert b'<div class="temperatuur">3.6</div>' in response.data
  assert b'<div class="waterstand">84 - 89</div>' in response.data
  assert b'<div class="verw0">3 / 6</div>' in response.data
  assert b'<div class="verw1">3 / 5</div>' in response.data
  assert mock_waterstand.called

@patch('zonnetijden.getweerinfo')
@patch('waterstand.haalwaterstand', return_value={'resultaat': 'OK', 'tijd': '23-11 16:50', 'nu': 84.0, 'morgen': 89.0})
@freeze_time("2024-11-23 16:50:00")
def test_weer_geenkey(mock_waterstand, mock_getweerinfo, mock_env_weerapikey, clear_cache, client):
  mock_getweerinfo.return_value = None

  response = client.get('/weer')
  assert b'<title>Vandaag in Hattem</title>' in response.data
  assert b'<div class="waterstand">84 - 89</div>' in response.data
  assert b'<div class="verw0"> / </div>' in response.data
  assert mock_waterstand.called

@patch('zonnetijden.getweerinfo')
@patch('waterstand.haalwaterstand', return_value={'resultaat': 'NOK', 'tekst': 'fout'})
def test_weer_error(mock_waterstand, mock_getweerinfo, mock_env_weerapikey, clear_cache, client):
  testdata = readjsonfromfile()

  mock_getweerinfo.return_value = testdata

  response = client.get('/weer')
  assert b'<title>Vandaag in Hattem</title>' in response.data
  assert b'<div class="temperatuur">3.6</div>' in response.data
  assert b'<div class="waterstand">- - -</div>' in response.data
  assert mock_waterstand.called


@freeze_time("2024-12-23 13:28:00")
def test_zon(mock_env_weerapikey, client):
  response = client.get('/zon')
  assert b'<title>Vandaag in Hattem</title>' in response.data
  assert b'<td>2024-12-12</td>' not in response.data
  assert b'<td>2024-12-13</td>' in response.data
  assert b'<td>2025-02-10</td>' in response.data
  assert b'<td>2025-02-11</td>' not in response.data


@freeze_time("2024-12-23 13:28:00")
def test_zon_zwolle_korter(mock_env_weerapikey, client):
  response = client.get('/zon?plaats=zwolle&terug=3&vooruit=3')
  assert b'<title>Vandaag in Zwolle</title>' in response.data
  assert b'<td>2024-12-19</td>' not in response.data
  assert b'<td>2024-12-20</td>' in response.data
  assert b'<td>2024-12-25</td>' in response.data
  assert b'<td>2024-12-26</td>' not in response.data


@freeze_time("2024-12-23 13:28:00")
def test_zon_fout_default(mock_env_weerapikey, client):
  response = client.get('/zon?terug=t&vooruit=v')
  assert b'<title>Vandaag in Hattem</title>' in response.data
  assert b'<td>2024-12-12</td>' not in response.data
  assert b'<td>2024-12-13</td>' in response.data
  assert b'<td>2025-02-10</td>' in response.data
  assert b'<td>2025-02-11</td>' not in response.data
