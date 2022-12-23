#!/bin/sh
gunicorn -w2 'datawarga.wsgi:application' --access-logfile=- -b 0.0.0.0