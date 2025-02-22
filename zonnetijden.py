""" Flexibel opvraagbare tijden van zonsopkomst en -ondergang """
import datetime
import locale
import os

import pytz
import requests
import waitress
import waterstand
from astral import LocationInfo
from astral.sun import sun
from cachetools import cached, TTLCache
from flask import Flask, render_template, request

app = Flask(__name__)
weerapikey = os.environ['WEER_API_KEY']
weercache = TTLCache(maxsize=1, ttl=900)
watercache = TTLCache(maxsize=1, ttl=7200)
locatiecache = TTLCache(maxsize=10, ttl=86400)


def leesjson(url):  # pragma: no cover
  """ Haal JSON van de URL op """
  try:
    req = requests.get(url, timeout=6, allow_redirects=False)
    return req.json()
  except (requests.exceptions.InvalidURL, requests.exceptions.HTTPError, IOError):
    return None


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
def getweerinfo():  # pragma: no cover
  """ Haal de informatie van het weer van Hattem op """
  url = f'https://weerlive.nl/api/weerlive_api_v2.php?key={weerapikey}&locatie=Hattem'
  weerinfo = leesjson(url)
  if weerinfo is None or \
      weerinfo.get('liveweer', None) is None or \
      weerinfo.get('liveweer')[0].get('fout') is not None:
    return None
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


@cached(locatiecache)
def getlocatieinfo(plaatsnaam):
  """ haal locatie op basis van een (plaats)naam op """
  url = f'https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q={plaatsnaam}'
  locatieinfo = leesjson(url)
  if locatieinfo is None or \
      locatieinfo.get('response', None) is None or \
      int(locatieinfo.get('response').get('numFound', 0)) == 0:
    return None
  centroide_ll = locatieinfo['response']['docs'][0]['centroide_ll']
  punten = centroide_ll.replace('POINT(', '').replace(')', '').split(' ')
  result = {'lat': float(punten[1]), 'lon': float(punten[0])}
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


def getweergegevens():
  """ Haal de gegevens van het weer van Hattem op """
  weerinfo = getweerinfo()
  gegevens = {}
  if weerinfo:
    temp = weerinfo['liveweer'][0]['temp']
    gtemp = weerinfo['liveweer'][0]['gtemp']
    max0 = weerinfo['wk_verw'][0 + bepaaldagerbij()]['max_temp']
    max1 = weerinfo['wk_verw'][1 + bepaaldagerbij()]['max_temp']
    max2 = weerinfo['wk_verw'][2 + bepaaldagerbij()]['max_temp']
    max3 = weerinfo['wk_verw'][3 + bepaaldagerbij()]['max_temp']
    max4 = weerinfo['wk_verw'][4]['max_temp']
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
  return gegevens


@app.route('/weer', methods=['GET'])
def weerget():
  """ Genereer de pagina met het weer en de zon van vandaag in Hattem """
  locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
  vandaag = datetime.date.today()
  gegevens = getinfohattem(str(vandaag))
  gegevens = gegevens | getweergegevens()
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
  gegevens['kleur'] = 'lawngreen'
  gegevens['dag'] = vandaag.strftime('%-d')
  gegevens['weekdag'] = vandaag.strftime('%A')
  gegevens['maand'] = vandaag.strftime('%B')
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
  except (TypeError, ValueError):
    argterug = '10'
  terug = -1 * int(argterug)

  try:
    int(argvooruit)
  except (TypeError, ValueError):
    argvooruit = '50'
  vooruit = int(argvooruit)

  plaatsgegevens = getlocatieinfo(plaats)
  if plaatsgegevens:
    lat = plaatsgegevens['lat']
    lon = plaatsgegevens['lon']
  else:
    plaats = 'Hattem (default)'
    lat = 52.479108
    lon = 6.060676
  vandaag = datetime.date.today()
  for i in range(terug, vooruit):
    dag = vandaag + datetime.timedelta(i)
    gegevens.append(getinfo(str(dag), plaats, lat, lon, True))

  return render_template('vandaag.html', plaats=plaats, rows=gegevens)


if __name__ == '__main__':
  waitress.serve(app, host="0.0.0.0", port=8083)
