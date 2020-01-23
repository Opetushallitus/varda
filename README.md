# Varda - Varhaiskasvatuksen tietovaranto

## Getting started

### Applikaation ajaminen dokkerilla

```
$ docker build -t varda .
$ docker run -it --net=host -e VARDA_ENVIRONMENT_TYPE='local-dev-env' -p 8080:8080 varda
```

Suuntaa selaimella osoitteeseen <http://localhost:8080>

### Tietokannan määrittely

Postgresql-tietokannan osoitteen voi määrittää ympäristömuuttujalla: 'POSTGRESQL_SERVICE_HOST'.
Jos ympäristömuuttujaa ei määritellä, käytetään oletuksena 'localhost'.


### Halutessasi voit ajaa testit lokaalisti

```
$ cd webapps; ./make_migrations.sh
$ python manage.py test varda -p "*tests.py"
```
