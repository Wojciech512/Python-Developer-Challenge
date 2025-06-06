FROM python:2

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev git libmemcached-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/tomwojcik-adverity/swapi.git /app/swapi

WORKDIR /app/swapi

RUN pip install --no-cache-dir -r /app/swapi/requirements.txt

COPY . /app/

EXPOSE 12345

COPY ./entrypoint.sh /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]