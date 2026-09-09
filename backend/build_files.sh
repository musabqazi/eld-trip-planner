#!/bin/bash
# Used by Vercel when building the Django API.
pip install -r requirements.txt
python manage.py migrate --noinput
