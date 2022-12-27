FROM python:3.11-slim

RUN apt update && apt install -y libpq-dev libpango-1.0-0 libpangoft2-1.0-0

RUN mkdir /app/
COPY requirements.txt /app/
RUN pip install -Ur /app/requirements.txt

ADD datawarga /app/datawarga

WORKDIR /app/datawarga

COPY entrypoint.sh /app/datawarga/
RUN chmod +x /app/datawarga/entrypoint.sh

RUN mkdir -p /app/datawarga/media/uploads

ENTRYPOINT [ "./entrypoint.sh" ]