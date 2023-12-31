""" Flexibel opvraagbare tijden van zonsopkomst en -ondergang """
import datetime

from flask import Flask, render_template
from flask import request

from astral import LocationInfo
from astral.sun import sun

import pytz

app = Flask(__name__)

def formatdate(date) :
    """ f """
    localdate = date.astimezone(pytz.timezone('Europe/Amsterdam'))
    formatteddate = datetime.datetime.strftime(localdate, '%Y-%m-%d')
    return formatteddate

def formattime(date) :
    """ f """
    localdate = date.astimezone(pytz.timezone('Europe/Amsterdam'))
    formatteddate = datetime.datetime.strftime(localdate, '%H:%M')
    return formatteddate

def formattimedelta(timedelta) :
    """ f """
    return str(timedelta).split(".", maxsplit=1)[0]

def berekenzonnetijden(datum, plaats, lat, lon) :
    """ f """
    datumdelen = datum.split('-')
    jaar = int(datumdelen[0])
    maand = int(datumdelen[1])
    dag = int(datumdelen[2])
    city = LocationInfo(plaats, 'Netherlands', 'Europe/Amsterdam', lat, lon)
    return sun(city.observer, date=datetime.date(jaar, maand, dag), tzinfo=city.timezone)

def getinfo(datum, plaats, lat, lon) :
    """ f """
    res = berekenzonnetijden(datum, plaats, lat, lon)

    opkomst  = res['sunrise']
    onder    = res['sunset']
    daglengs = onder - opkomst
    result = {}
    result['datum'] = formatdate(opkomst)
    result['op'] = formattime(opkomst)
    result['onder'] = formattime(onder)
    result['daglengte'] = formattimedelta(daglengs)
    return result

def getinfohattem(datum) :
    """ f """
    return getinfo(datum, 'Hattem', 52.479108, 6.060676)

@app.route('/vandaag', methods=['GET'])
def vandaagget():
    """ f """
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

    return render_template('vandaag.html', plaats = 'Hattem', rows = gegevens)

@app.route('/vandaaglang', methods=['GET'])
def vandaaggetlang():
    """ f """
    gegevens = []
    plaats = request.args.get('plaats')
    argterug = request.args.get('terug')
    argvooruit = request.args.get('vooruit')

    if plaats is None :
        plaats = 'Hattem'
    else :
        plaats = plaats.capitalize()

    try :
        int(argterug)
    except TypeError :
        print('standaard terug 10')
        argterug = '10'
    terug = -1 * int(argterug)

    try :
        int(argvooruit)
    except TypeError :
        print('standaard vooruit 50')
        argvooruit = '50'
    vooruit = int(argvooruit)
    if plaats == 'Zwolle' :
        lat = 52.537563
        lon = 6.11083
    else :
        lat = 52.479108
        lon = 6.060676
    vandaag = datetime.date.today()
    for i in range(terug, vooruit) :
        dag = vandaag + datetime.timedelta(i)
        gegevens.append(getinfo(str(dag), plaats, lat, lon))

    return render_template('vandaag.html', plaats = plaats, rows = gegevens)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8083, debug=False)
