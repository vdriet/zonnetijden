""" Flexibel opvraagbare tijden van zonsopkomst en -ondergang """
import datetime
import json
import locale
import os

from urllib.request import urlopen, Request

from astral import LocationInfo
from astral.sun import sun

from flask import Flask, render_template
from flask import request

from cachetools import cached, TTLCache

import pytz
import waitress

from waterstand import haalwaterstand

app = Flask(__name__)
weerapikey = os.environ['WEER_API_KEY']
weercache = TTLCache(maxsize=1, ttl=300)
watercache = TTLCache(maxsize=1, ttl=7200)


def leesjson(url):
  """ Haal JSON van de URL op """
  req = Request(url=url)
  with urlopen(req) as response:
    contenttekst = response.read().decode('utf-8')
    contentjson = json.loads(contenttekst)
    return contentjson


def formatdate(date):
  """ Formateer de datum/tijd naar alleen de datum """
  localdate = date.astimezone(pytz.timezone('Europe/Amsterdam'))
  return datetime.datetime.strftime(localdate, '%Y-%m-%d')


def formattime(date):
  """ Formateer de datum/tijd naar de tijd """
  localdate = date.astimezone(pytz.timezone('Europe/Amsterdam'))
  return datetime.datetime.strftime(localdate, '%H:%M')


def formattimedelta(timedelta):
  """ Formater het tijdsverschil naar een tijd """
  return str(timedelta).split(".", maxsplit=1)[0]


def berekenzonnetijden(datum, plaats, lat, lon):
  """ Bereken de tijd van zonsopkomst en ondergang van de gegeven datum en plek """
  datumdelen = datum.split('-')
  jaar = int(datumdelen[0])
  maand = int(datumdelen[1])
  dag = int(datumdelen[2])
  city = LocationInfo(plaats, 'Netherlands', 'Europe/Amsterdam', lat, lon)
  return sun(city.observer, date=datetime.date(jaar, maand, dag), tzinfo=city.timezone)


def getinfo(datum, plaats, lat, lon):
  """ Haal de informatie van de zon op gegeven datum en plaats """
  res = berekenzonnetijden(datum, plaats, lat, lon)

  opkomst = res['sunrise']
  onder = res['sunset']
  result = {'datum': formatdate(opkomst),
            'op': formattime(opkomst),
            'onder': formattime(onder),
            'daglengte': formattimedelta(onder - opkomst)}
  return result


def getinfohattem(datum):
  """ Haal de gegevens van Hattem op de gegeven datum """
  return getinfo(datum, 'Hattem', 52.479108, 6.060676)


@app.route('/vandaag', methods=['GET'])
def vandaagget():
  """ Toon de gegevens van de zon van vandaag en enige andere datums """
  gegevens = []

  vandaag = datetime.date.today()

  dagminus4w = vandaag - datetime.timedelta(28)
  dagminus1w = vandaag - datetime.timedelta(7)
  dagplus1w = vandaag + datetime.timedelta(7)
  dagplus4w = vandaag + datetime.timedelta(28)

  gegevens.append(getinfohattem(str(dagminus4w)))
  gegevens.append(getinfohattem(str(dagminus1w)))
  gegevens.append(getinfohattem(str(vandaag)))
  gegevens.append(getinfohattem(str(dagplus1w)))
  gegevens.append(getinfohattem(str(dagplus4w)))

  return render_template('vandaag.html', plaats='Hattem', rows=gegevens)


@cached(weercache)
def getweerinfo():
  """ Haal de gegevens van het weer van Hattem op """
  url = f'https://weerlive.nl/api/weerlive_api_v2.php?key={weerapikey}&locatie=Hattem'
  weerinfo = leesjson(url)
  return weerinfo


@cached(watercache)
def getwaterinfo():
  """ Haal de gegevens van de waterstand bij Zwolle op """
  waterstand = haalwaterstand('Katerveer', 'KATV')
  result = {'hoogtenu': int(waterstand['nu']),
            'hoogtemorgen': int(waterstand['morgen'])
            }
  return result


@app.route('/weer', methods=['GET'])
def weerget():
  """ Genereer de pagina met het weer en de zon van vandaag in Hattem """
  locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
  vandaag = datetime.date.today()
  gegevens = getinfohattem(str(vandaag))
  weerinfo = getweerinfo()
  waterinfo = getwaterinfo()
  gegevens['dag'] = vandaag.strftime('%-d')
  gegevens['weekdag'] = vandaag.strftime('%A')
  gegevens['maand'] = vandaag.strftime('%B')
  gegevens['temp'] = weerinfo['liveweer'][0]['temp']
  gegevens['gtemp'] = weerinfo['liveweer'][0]['gtemp']
  gegevens['samenv'] = weerinfo['liveweer'][0]['samenv']
  gegevens['verw'] = weerinfo['liveweer'][0]['verw']
  gegevens['windr'] = weerinfo['liveweer'][0]['windr']
  gegevens['windbft'] = weerinfo['liveweer'][0]['windbft']
  gegevens['max0'] = weerinfo['wk_verw'][0]['max_temp']
  gegevens['min0'] = weerinfo['wk_verw'][0]['min_temp']
  gegevens['max1'] = weerinfo['wk_verw'][1]['max_temp']
  gegevens['min1'] = weerinfo['wk_verw'][1]['min_temp']
  gegevens['max2'] = weerinfo['wk_verw'][2]['max_temp']
  gegevens['min2'] = weerinfo['wk_verw'][2]['min_temp']
  gegevens['max3'] = weerinfo['wk_verw'][3]['max_temp']
  gegevens['min3'] = weerinfo['wk_verw'][3]['min_temp']
  gegevens['bron'] = weerinfo['api'][0]['bron']
  gegevens['waterstand'] = waterinfo['hoogtenu']
  gegevens['waterstandmorgen'] = waterinfo['hoogtemorgen']
  return render_template('weer.html', plaats='Hattem', gegevens=gegevens)


@app.route('/zon', methods=['GET'])
def zonget():
  """ Haal de gegevens van de zon op """
  gegevens = []
  plaats = request.args.get('plaats')
  argterug = request.args.get('terug')
  argvooruit = request.args.get('vooruit')

  if plaats is None:
    plaats = 'Hattem'
  else:
    plaats = plaats.capitalize()

  try:
    int(argterug)
  except TypeError:
    print('standaard terug 10')
    argterug = '10'
  terug = -1 * int(argterug)

  try:
    int(argvooruit)
  except TypeError:
    print('standaard vooruit 50')
    argvooruit = '50'
  vooruit = int(argvooruit)
  if plaats == 'Zwolle':
    lat = 52.537563
    lon = 6.11083
  else:
    lat = 52.479108
    lon = 6.060676
  vandaag = datetime.date.today()
  for i in range(terug, vooruit):
    dag = vandaag + datetime.timedelta(i)
    gegevens.append(getinfo(str(dag), plaats, lat, lon))

  return render_template('vandaag.html', plaats=plaats, rows=gegevens)


if __name__ == '__main__':
  waitress.serve(app, host="0.0.0.0", port=8083)
