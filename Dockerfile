FROM python:3.13

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y locales 
RUN echo "nl_NL.UTF-8 UTF-8" > /etc/locale.gen && locale-gen
ENV TZ=Europe/Amsterdam

COPY requirements.txt /usr/src/app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY /*.py /usr/src/app/
COPY /templates/* /usr/src/app/templates/

EXPOSE 8080

CMD [ "python", "-u", "zonnetijden.py" ]
