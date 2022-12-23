FROM python:3.10-alpine

RUN apk --update --upgrade --no-cache add py3-pip gcc musl-dev \
    python3-dev pango zlib-dev jpeg-dev openjpeg-dev g++ \
    libffi-dev fontconfig ttf-freefont font-noto terminus-font \
    libpq

RUN fc-cache -f \ 
   && fc-list | sort 

RUN mkdir /app/
COPY requirements.txt /app/
RUN pip install -Ur /app/requirements.txt

ADD datawarga /app/datawarga

WORKDIR /app/datawarga

RUN python manage.py collectstatic

COPY entrypoint.sh /app/datawarga/
RUN chmod +x /app/datawarga/entrypoint.sh

RUN mkdir -p /app/datawarga/media/uploads

ENTRYPOINT [ "./entrypoint.sh" ]