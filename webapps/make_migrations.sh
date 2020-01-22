#!/bin/bash

read -p "This will erase your local DB, and set it up again. Are you sure you want to continue? <Y/n> " prompt
if [[ $prompt == "y" || $prompt == "Y" || $prompt == "yes" || $prompt == "Yes" ]]
then

  echo "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'varda_db';" |python manage.py dbshell --database varda_db_superuser

  sudo -u postgres dropdb varda_db
  sudo -u postgres createdb -O varda_admin -E 'UTF8' varda_db

  # find ./varda/migrations/ -type f ! -name '__init__.py' -delete

  rm -fr varda/migrations/__pycache__/*

  python manage.py makemigrations
  python manage.py migrate

  python manage.py populate_history --auto

  python manage.py loaddata varda/unit_tests/fixture_basics.json
  python manage.py load_test_data

  django-admin compilemessages  # To compile translation-messages (.mo files)

fi
