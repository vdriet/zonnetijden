""" 
Module voor het berekenen en weergeven van zonsopkomst- en ondergangstijden.

Dit module biedt functionaliteit voor:
- Opvragen van zonsopkomst en -ondergang voor willekeurige locaties in Nederland
- Weergeven van zontijden voor specifieke datums
- Tonen van weer- en waterstandinformatie voor Hattem
- Cachen van opgevraagde gegevens voor betere performance
"""
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


def leesjson(url: str) -> dict:
  """ 
  Haalt JSON-data op van een gegeven URL.
  
  Args:
      url: De URL waarvan de JSON-data opgehaald moet worden
      
  Returns:
      dict: De opgehaalde JSON-data als dictionary
      {}: Als er een fout optreedt bij het ophalen
  """
  try:
    req = requests.get(url, timeout=6, allow_redirects=False)
    return req.json()
  except (requests.exceptions.InvalidURL,
          requests.exceptions.HTTPError,
          IOError):
    return {}


def formatdate(date: datetime) -> str:
  """
  Converteert een datetime object naar een datum string.
  
  Args:
      date: datetime object dat geformatteerd moet worden
      
  Returns:
      str: Geformatteerde datum in YYYY-MM-DD formaat
  """
  localdate = date.astimezone(pytz.timezone('Europe/Amsterdam'))
  return datetime.datetime.strftime(localdate, '%Y-%m-%d')


def formattime(date: datetime, seconds: bool = False) -> str:
  """
  Converteert een datetime object naar een tijd string.
  
  Args:
      date: datetime object dat geformatteerd moet worden
      seconds: Of seconden meegenomen moeten worden in de output
      
  Returns:
      str: Geformatteerde tijd in HH:MM- of HH:MM:SS-formaat
  """
  localdate = date.astimezone(pytz.timezone('Europe/Amsterdam'))
  if seconds:
    formaat = '%H:%M:%S'
  else:
    formaat = '%H:%M'
  return datetime.datetime.strftime(localdate, formaat)


def formattimedelta(timedelta):
  """
  Converteert een timedelta naar een leesbare tijd string.
  
  Args:
      timedelta: Het tijdsverschil dat geformatteerd moet worden
      
  Returns:
      str: Geformatteerd tijdsverschil in HH:MM:SS=formaat
  """
  return str(timedelta).split(".", maxsplit=1)[0]


def berekenzonnetijden(datum: str, plaats: str, lat: float, lon: float) -> dict:
  """
  Berekent zonsopkomst en -ondergang voor een specifieke locatie en datum.
  
  Args:
      datum: Datum waarvoor de tijden berekend moeten worden (YYYY-MM-DD)
      plaats: Naam van de plaats
      lat: Breedtegraad van de locatie
      lon: Lengtegraad van de locatie
      
  Returns:
      dict: Dictionary met zonsopkomst, -ondergang en andere zontijden
  """
  datumdelen = datum.split('-')
  jaar = int(datumdelen[0])
  maand = int(datumdelen[1])
  dag = int(datumdelen[2])
  city = LocationInfo(plaats, 'Netherlands', 'Europe/Amsterdam', lat, lon)
  return sun(city.observer, date=datetime.date(jaar, maand, dag), tzinfo=city.timezone)


def getinfo(datum: str, plaats: str, lat: float, lon: float, seconds: bool = False) -> dict:
  """
  Verzamelt alle zoninformatie voor een specifieke datum en locatie.
  
  Args:
      datum: Datum waarvoor de informatie opgevraagd wordt
      plaats: Naam van de plaats
      lat: Breedtegraad van de locatie
      lon: Lengtegraad van de locatie
      seconds: Of tijden met seconden weergegeven moeten worden
      
  Returns:
      dict: Dictionary met datum, zonsopkomst, -ondergang en daglengte
  """
  res = berekenzonnetijden(datum, plaats, lat, lon)

  opkomst = res['sunrise']
  onder = res['sunset']
  result = {'datum': formatdate(opkomst),
            'op': formattime(opkomst, seconds),
            'onder': formattime(onder, seconds),
            'daglengte': formattimedelta(onder - opkomst)}
  return result


def getinfohattem(datum: str, seconds: bool = False) -> dict:
  """
  Verzamelt zoninformatie specifiek voor Hattem.
  
  Args:
      datum: Datum waarvoor de informatie opgevraagd wordt
      seconds: Of tijden met seconden weergegeven moeten worden
      
  Returns:
      dict: Dictionary met zoninformatie voor Hattem
  """
  return getinfo(datum, 'Hattem', 52.479108, 6.060676, seconds)


@app.route('/vandaag', methods=['GET'])
def vandaagget() -> str:
  """
  Genereert een overzichtspagina met zontijden voor meerdere datums.
  
  Returns:
      str: HTML-pagina met zontijden van verschillende datums
  """
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
def getweerinfo() -> dict:
  """
  Haalt de actuele informatie over het weer voor Hattem op via de weerlive.nl-API.

  Returns:
      dict: Dictionary met weergegevens inclusief temperatuur, windkracht en verwachting
      None: Als er een fout optreedt bij het ophalen van de gegevens
  """
  url = f'https://weerlive.nl/api/weerlive_api_v2.php?key={weerapikey}&locatie=Hattem'
  weerinfo = leesjson(url)
  if weerinfo == {} or \
      weerinfo.get('liveweer', None) is None or \
      weerinfo.get('liveweer')[0].get('fout') is not None:
    return {}
  return weerinfo


@cached(watercache)
def getwaterinfo() -> dict:
  """
  Haalt de actuele waterstand bij het Katerveer in Zwolle op.
  
  De gegevens worden opgehaald uit de waterstand module en gecachet voor 2 uur.
  
  Returns:
      dict: Dictionary met huidige en voorspelde waterstand voor morgen
      dict: Lege dictionary als er een fout optreedt
  """
  stand = waterstand.haalwaterstand('Katerveer', 'KATV')
  if stand['resultaat'] == 'NOK':
    return {}
  result = {'hoogtenu': int(stand['nu']),
            'hoogtemorgen': int(stand['morgen'])
            }
  return result


@cached(locatiecache)
def getlocatieinfo(plaatsnaam: str) -> dict:
  """
  Haalt locatiegegevens op voor een opgegeven plaatsnaam.
  
  Args:
      plaatsnaam: Naam van de plaats of postcode waarvoor de coördinaten opgevraagd worden
      
  Returns:
      dict: Dictionary met latitude en longitude coördinaten
      None: Als er geen locatie gevonden kan worden
  """
  url = f'https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q={plaatsnaam}'
  locatieinfo = leesjson(url)
  if locatieinfo == {} or \
      locatieinfo.get('response', None) is None or \
      int(locatieinfo.get('response').get('numFound', 0)) == 0:
    return {}
  centroide_ll = locatieinfo['response']['docs'][0]['centroide_ll']
  punten = centroide_ll.replace('POINT(', '').replace(')', '').split(' ')
  result = {'lat': float(punten[1]), 'lon': float(punten[0])}
  return result


def bepaaltoenamekleur(verschil: int) -> str:
  """
  Bepaalt de achtergrondkleur voor een temperatuurstijging.
  
  Args:
      verschil: Het aantal graden temperatuurstijging
      
  Returns:
      str: CSS-kleurnaam passend bij de temperatuurstijging
  """
  if verschil == 1:
    return 'yellow'
  if verschil == 2:
    return 'gold'
  if verschil == 3:
    return 'orange'
  if verschil == 4:
    return 'darkorange'
  return 'orangered'


def bepaalafnamekleur(verschil: int) -> str:
  """
  Bepaalt de achtergrondkleur voor een temperatuurdaling.
  
  Args:
      verschil: Het aantal graden temperatuurdaling
      
  Returns:
      str: CSS-kleurnaam passend bij de temperatuurdaling
  """
  if verschil == -1:
    return 'lightblue'
  if verschil == -2:
    return 'lightskyblue'
  if verschil == -3:
    return 'deepskyblue'
  if verschil == -4:
    return 'dodgerblue'
  return 'royalblue'


def bepaalkleur(max0: int, max1: int) -> str:
  """
  Bepaalt de achtergrondkleur op basis van temperatuurverschil.
  
  Args:
      max0: Huidige maximumtemperatuur
      max1: Nieuwe maximumtemperatuur
      
  Returns:
      str: CSS-kleurnaam passend bij het temperatuurverschil
  """
  verschil = max1 - max0
  if verschil > 0:
    return bepaaltoenamekleur(verschil)
  if verschil < 0:
    return bepaalafnamekleur(verschil)
  return 'lawngreen'


def bepaalwaterkleur(stand: int, waterstandmorgen: int) -> tuple[str, str]:
  """
  Bepaalt de weergavekleuren voor waterstanden.
  
  Args:
      stand: Huidige waterstand
      waterstandmorgen: Voorspelde waterstand voor morgen
      
  Returns:
      tuple: Twee CSS-kleurnamen voor huidige en voorspelde waterstand
  """
  if waterstandmorgen > stand:
    return 'lightblue', 'dodgerblue'
  return 'dodgerblue', 'lightblue'


def bepaaldagerbij() -> int:
  """
  Bepaalt of de voorspelling van vandaag of morgen gebruikt moet worden.
  
  Returns:
      int: 0 voor vandaag, 1 voor morgen (na 15:00)
  """
  if datetime.datetime.now().hour > 15:
    return 1
  return 0


def getweergegevens() -> dict:
  """
  Verzamelt actuele weergegevens voor Hattem.
  
  Returns:
      dict: Dictionary met temperatuur, windkracht, verwachting en andere weergegevens
  """
  weerinfo = getweerinfo()
  gegevens = {}
  if weerinfo != {}:
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
def weerget() -> str:
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
def zonget() -> str:
  """
  Genereert een overzicht van zontijden voor een opgegeven plaats en periode.
  
  Query parameters:
      plaats: Naam van de plaats (default: Hattem)
      terug: Aantal dagen terug (default: 10)
      vooruit: Aantal dagen vooruit (default: 50)
  
  Returns:
      str: HTML-pagina met zontijden voor de opgegeven periode
  """
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
