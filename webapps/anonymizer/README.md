## Database anonymization

You can use the following management-command to generate anonymized dataset.
By default creating a dataset of 800 000 henkilot.

```
$ python manage.py create_anonymized_dataset
```

You can also set the number of henkilot yourself. Useful in testing.

```
python manage.py create_anonymized_dataset --number_of_henkilot 100
```

After dataset has been created, you can perform the actual anonymization.
You can use the following management-command to anonymize the database (using the above dataset).

```
$ python manage.py anonymize_data
```

The output should be similar to:

```
$ python manage.py anonymize_data
Anonymizing data (SQL part)...
SQL part successfully executed in 553.479713095352 seconds
Anonymizing data (Python part / Hetut and lastnames)...
Anonymized data was not found locally. Lets fetch it.
This is how many were actually updated: 656924
Python part successfully executed in 162.19064091797918 seconds
Finalizing the dump.
Installed 9 object(s) from 1 fixture(s)
Finalizing the dump executed in 11.84185007121414 seconds
```
