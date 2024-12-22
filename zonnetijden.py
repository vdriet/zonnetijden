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

import waterstand

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


def formattime(date, seconds=False):
  """ Formateer de datum/tijd naar de tijd """
  localdate = date.astimezone(pytz.timezone('Europe/Amsterdam'))
  if seconds:
    formaat = '%H:%M:%S'
  else:
    formaat = '%H:%M'
  return datetime.datetime.strftime(localdate, formaat)


def formattimedelta(timedelta):
  """ Formateer het tijdsverschil naar een tijd """
  return str(timedelta).split(".", maxsplit=1)[0]


def berekenzonnetijden(datum, plaats, lat, lon):
  """ Bereken de tijd van zonsopkomst en ondergang van de gegeven datum en plek """
  datumdelen = datum.split('-')
  jaar = int(datumdelen[0])
  maand = int(datumdelen[1])
  dag = int(datumdelen[2])
  city = LocationInfo(plaats, 'Netherlands', 'Europe/Amsterdam', lat, lon)
  return sun(city.observer, date=datetime.date(jaar, maand, dag), tzinfo=city.timezone)


def getinfo(datum, plaats, lat, lon, seconds=False):
  """ Haal de informatie van de zon op gegeven datum en plaats """
  res = berekenzonnetijden(datum, plaats, lat, lon)

  opkomst = res['sunrise']
  onder = res['sunset']
  result = {'datum': formatdate(opkomst),
            'op': formattime(opkomst, seconds),
            'onder': formattime(onder, seconds),
            'daglengte': formattimedelta(onder - opkomst)}
  return result


def getinfohattem(datum, seconds=False):
  """ Haal de gegevens van Hattem op de gegeven datum """
  return getinfo(datum, 'Hattem', 52.479108, 6.060676, seconds)


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
  stand = waterstand.haalwaterstand('Katerveer', 'KATV')
  if stand['resultaat'] == 'NOK':
    return {}
  result = {'hoogtenu': int(stand['nu']),
            'hoogtemorgen': int(stand['morgen'])
            }
  return result


def bepaaltoenamekleur(verschil):
  """ Bepaal kleur bij toename van temperatuur """
  if verschil == 1:
    return 'yellow'
  if verschil == 2:
    return 'gold'
  if verschil == 3:
    return 'orange'
  if verschil == 4:
    return 'darkorange'
  return 'orangered'


def bepaalafnamekleur(verschil):
  """ Bepaal kleur bij afname van temperatuur """
  if verschil == -1:
    return 'lightblue'
  if verschil == -2:
    return 'lightskyblue'
  if verschil == -3:
    return 'deepskyblue'
  if verschil == -4:
    return 'dodgerblue'
  return 'royalblue'


def bepaalkleur(max0, max1):
  """ Bepaal achtergrondkleur voor de temperatuur """
  verschil = max1 - max0
  if verschil > 0:
    return bepaaltoenamekleur(verschil)
  if verschil < 0:
    return bepaalafnamekleur(verschil)
  return 'lawngreen'


def bepaalwaterkleur(stand, waterstandmorgen):
  """ Bepaal de kleuren van de waterstand """
  if waterstandmorgen > stand:
    return 'lightblue', 'dodgerblue'
  return 'dodgerblue', 'lightblue'


def bepaaldagerbij():
  """ bepaal of de verwachting van vandaag of morgen de basis zijn """
  if datetime.datetime.now().hour > 15:
    return 1
  return 0


@app.route('/weer', methods=['GET'])
def weerget():
  """ Genereer de pagina met het weer en de zon van vandaag in Hattem """
  locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
  vandaag = datetime.date.today()
  gegevens = getinfohattem(str(vandaag), True)
  weerinfo = getweerinfo()
  waterinfo = getwaterinfo()
  if not waterinfo:
    stand = '-'
    waterstandmorgen = '-'
    waterkleur1 = 'red'
    waterkleur2 = 'red'
  else:
    stand = waterinfo['hoogtenu']
    waterstandmorgen = waterinfo['hoogtemorgen']
    waterkleur1, waterkleur2 = bepaalwaterkleur(stand, waterstandmorgen)
  temp = weerinfo['liveweer'][0]['temp']
  gtemp = weerinfo['liveweer'][0]['gtemp']
  max0 = weerinfo['wk_verw'][0 + bepaaldagerbij()]['max_temp']
  max1 = weerinfo['wk_verw'][1 + bepaaldagerbij()]['max_temp']
  max2 = weerinfo['wk_verw'][2 + bepaaldagerbij()]['max_temp']
  max3 = weerinfo['wk_verw'][3 + bepaaldagerbij()]['max_temp']
  max4 = weerinfo['wk_verw'][4]['max_temp']
  gegevens['kleur'] = 'lawngreen'
  gegevens['dag'] = vandaag.strftime('%-d')
  gegevens['weekdag'] = vandaag.strftime('%A')
  gegevens['maand'] = vandaag.strftime('%B')
  gegevens['temp'] = temp
  gegevens['gtemp'] = gtemp
  gegevens['gevoelskleur'] = bepaalkleur(int(temp), int(gtemp))
  gegevens['samenv'] = weerinfo['liveweer'][0]['samenv']
  gegevens['verw'] = weerinfo['liveweer'][0]['verw']
  gegevens['windr'] = weerinfo['liveweer'][0]['windr']
  gegevens['windbft'] = weerinfo['liveweer'][0]['windbft']
  gegevens['max0'] = max0
  gegevens['min0'] = weerinfo['wk_verw'][0 + bepaaldagerbij()]['min_temp']
  gegevens['max1'] = max1
  gegevens['min1'] = weerinfo['wk_verw'][1 + bepaaldagerbij()]['min_temp']
  gegevens['kleur1'] = bepaalkleur(max0, max1)
  gegevens['max2'] = max2
  gegevens['min2'] = weerinfo['wk_verw'][2 + bepaaldagerbij()]['min_temp']
  gegevens['kleur2'] = bepaalkleur(max0, max2)
  gegevens['max3'] = max3
  gegevens['min3'] = weerinfo['wk_verw'][3 + bepaaldagerbij()]['min_temp']
  gegevens['kleur3'] = bepaalkleur(max0, max3)
  gegevens['kleur4'] = bepaalkleur(max0, max4)
  gegevens['bron'] = weerinfo['api'][0]['bron']
  gegevens['waterstand'] = stand
  gegevens['waterstandmorgen'] = waterstandmorgen
  gegevens['waterkleur1'] = waterkleur1
  gegevens['waterkleur2'] = waterkleur2
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
    gegevens.append(getinfo(str(dag), plaats, lat, lon, True))

  return render_template('vandaag.html', plaats=plaats, rows=gegevens)


if __name__ == '__main__':
  waitress.serve(app, host="0.0.0.0", port=8083)
