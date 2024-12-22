import json
from unittest.mock import patch

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


def test_vandaag(mock_env_weerapikey, client):
  response = client.get('/vandaag')
  assert b"1" in response.data


def readjsonfromfile():
  f = open('tests/testdata_weerinfo.json', 'r')
  return json.loads(f.read())


@patch('zonnetijden.getweerinfo')
@patch('waterstand.haalwaterstand', return_value={'resultaat': 'OK', 'tijd': '23-11 16:50', 'nu': 84.0, 'morgen': 89.0})
def test_weer(mock_waterstand, mock_getweerinfo, mock_env_weerapikey, clear_cache, client):
  testdata = readjsonfromfile()

  mock_getweerinfo.return_value = testdata

  response = client.get('/weer')
  assert b'<title>Vandaag in Hattem</title>' in response.data
  assert b'<div class="temperatuur">3.6</div>' in response.data
  assert b'<div class="waterstand">84 - 89</div>' in response.data
  assert mock_waterstand.called


@patch('zonnetijden.getweerinfo')
@patch('waterstand.haalwaterstand', return_value={'resultaat': 'NOK', 'tekst': 'fout'})
def test_weer_error(mock_waterstand, mock_getweerinfo, mock_env_weerapikey, clear_cache, client):
  testdata = readjsonfromfile()

  mock_getweerinfo.return_value = testdata

  response = client.get('/weer')
  assert b'<title>Vandaag in Hattem</title>' in response.data
  assert b'<div class="temperatuur">3.6</div>' in response.data
  # fout vanwege de cache
  assert b'<div class="waterstand">- - -</div>' in response.data
  assert mock_waterstand.called


def test_zon(mock_env_weerapikey, client):
  response = client.get('/zon')
  assert b"1" in response.data

# @patch('sslcheck.getinfo', side_effect=None)
# def test_sslcheck_post(mock_info, client):
#   client.post('/sslcheck',
#               headers={'Apikey': 'MySecret'
#                 , 'Hostname': 'example.com'})
#   assert mock_info.called
