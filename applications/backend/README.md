# Varda - National data warehouse for early childhood education data

### Data model

The data model for Varda is publicly available at 
- https://virkailija.opintopolku.fi/varda/julkinen/tietomalli

### Varda is built using the following open source technologies
- Backend
    * Django web framework (https://www.djangoproject.com/)
    * Postgresql database (https://www.postgresql.org/)
- Frontend
    * Angular UI framework (https://angular.io/)

### Backend

#### Development

```
$ pip install -r requirements.txt
$ pre-commit install
```

Set database

You can set an environment variable 'POSTGRESQL_SERVICE_HOST' for Postgresql IP. If it's not set, a
'localhost' will be used.

```
$ cd webapps
$ ./make_migrations.sh
```

Open development server (http://localhost:8000/)

```
$ python manage.py runserver &
```

Running tests

```
$ python manage.py test varda -p "*tests.py"
```
