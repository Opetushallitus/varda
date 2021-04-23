import base64
import hashlib
import json
import logging
import os
import requests
import sys


logger = logging.getLogger(__name__)

PROD_HOSTNAME = os.getenv('PROD_HOSTNAME')
PROD_API_USERNAME = os.getenv('PROD_API_USERNAME')
PROD_API_PASSWORD = os.getenv('PROD_API_PASSWORD')
ANONYMIZED_ENV_HOSTNAME = os.getenv('ANONYMIZED_ENV_HOSTNAME')
ANONYMIZED_ENV_API_USERNAME = os.getenv('ANONYMIZED_ENV_API_USERNAME')
ANONYMIZED_ENV_API_PASSWORD = os.getenv('ANONYMIZED_ENV_API_PASSWORD')


def hash_string(string):
    """
    Return a SHA-256 hash of the given string
    TODO: Use same as in varda.misc.py
    """
    return hashlib.sha256(string.encode('utf-8')).hexdigest()


def base64_encoding(string_to_be_encoded):
    return base64.b64encode(bytes(string_to_be_encoded, 'utf-8')).decode('utf-8')


def get_authentication_headers(prod=False):
    if prod:
        credentials = PROD_API_USERNAME + ':' + PROD_API_PASSWORD
    else:
        credentials = ANONYMIZED_ENV_API_USERNAME + ':' + ANONYMIZED_ENV_API_PASSWORD

    b64_credentials = base64_encoding(credentials)
    return {'Accept': 'application/json', 'Content-Type': 'application/json',
            'Authorization': f'Basic {b64_credentials}'}


def get_access_token(prod=False):
    if prod:
        hostname = PROD_HOSTNAME
    else:
        hostname = ANONYMIZED_ENV_HOSTNAME
    api_endpoint = '/api/user/apikey/'
    try:
        r = requests.get(f'https://{hostname}{api_endpoint}', headers=get_authentication_headers(prod),
                         allow_redirects=False)
    except requests.exceptions.RequestException as e:
        logger.error(e)
        sys.exit(1)

    status_code = r.status_code
    if status_code != 200:
        logger.error(f'Error! HTTP status code: {status_code}')
        logger.error(r.headers)
        logger.error(r.content)
        sys.exit(1)

    try:
        data = json.loads(r.content)
    except ValueError as e:
        logger.error(e)
        sys.exit(1)
    return data['token']


def get_http_header(prod=False):
    auth_token = get_access_token(prod)
    return {'Accept': 'application/json', 'Content-Type': 'application/json',
            'Authorization': f'Token {auth_token}'}


def get_request(api_endpoint, prod=False):
    if prod:
        hostname = PROD_HOSTNAME
    else:
        hostname = ANONYMIZED_ENV_HOSTNAME

    url = f'https://{hostname}{api_endpoint}'
    try:
        r = requests.get(url, headers=get_http_header(prod))
    except requests.exceptions.RequestException as e:
        logger.error(e)
        sys.exit(2)

    status_code = r.status_code
    if status_code != 200:
        logger.error(f'Error! HTTP status code: {status_code}. Url: {url}')
        logger.error(r.headers)
        logger.error(r.content)
        sys.exit(2)

    try:
        data = json.loads(r.content)
    except ValueError as e:
        logger.error(e)
        sys.exit(2)
    return data


def check_environment_variables():
    environment_variables = [
        'PROD_HOSTNAME',
        'PROD_API_USERNAME',
        'PROD_API_PASSWORD',
        'ANONYMIZED_ENV_HOSTNAME',
        'ANONYMIZED_ENV_API_USERNAME',
        'ANONYMIZED_ENV_API_PASSWORD'
    ]

    for env_variable in environment_variables:
        if env_variable not in os.environ:
            logger.error('Error: ' + env_variable + ' env-variable missing.')
            sys.exit(3)


def basic_anonymization_validation(anonymized_data_yhteenveto):
    """
    General validation that we have "a lot" of data. This only validates that the
    anonymization hasn't accidentally removed most of the data.
    """
    MIN_ACCEPTABLE_NO_OF_HENKILOT = 500000
    MIN_ACCEPTABLE_NO_OF_VAKAJARJESTAJAT = 1300
    MIN_ACCEPTABLE_NO_OF_TOIMIPAIKAT = 5000
    MIN_ACCEPTABLE_NO_OF_VARHAISKASVATUSSUHTEET = 400000
    MIN_ACCEPTABLE_NO_OF_TYONTEKIJAT = 5000
    MIN_ACCEPTABLE_NO_OF_TYOSKENTELYPAIKAT = 6000
    MIN_ACCEPTABLE_NO_OF_MAKSUTIEDOT = 300000

    """
    Set parameter to True if not enough data, i.e. anonymization failed.
    """
    henkilot = anonymized_data_yhteenveto['no_of_henkilot'] < MIN_ACCEPTABLE_NO_OF_HENKILOT
    vakajarjestajat = anonymized_data_yhteenveto['no_of_vakajarjestajat'] < MIN_ACCEPTABLE_NO_OF_VAKAJARJESTAJAT
    toimipaikat = anonymized_data_yhteenveto['no_of_toimipaikat'] < MIN_ACCEPTABLE_NO_OF_TOIMIPAIKAT
    varhaiskasvatussuhteet = anonymized_data_yhteenveto['no_of_varhaiskasvatussuhteet'] < MIN_ACCEPTABLE_NO_OF_VARHAISKASVATUSSUHTEET
    tyontekijat = anonymized_data_yhteenveto['no_of_tyontekijat'] < MIN_ACCEPTABLE_NO_OF_TYONTEKIJAT
    tyoskentelypaikat = anonymized_data_yhteenveto['no_of_tyoskentelypaikat'] < MIN_ACCEPTABLE_NO_OF_TYOSKENTELYPAIKAT
    maksutiedot = anonymized_data_yhteenveto['no_of_maksutiedot'] < MIN_ACCEPTABLE_NO_OF_MAKSUTIEDOT

    basic_data_validation_results = [henkilot, vakajarjestajat, toimipaikat, varhaiskasvatussuhteet,
                                     tyontekijat, tyoskentelypaikat, maksutiedot]
    if any(basic_data_validation_results):
        logger.error('Error: Anonymization failed. Not enough data.')
        sys.exit(4)


def validate_id_is_same(anonymized_henkilo_id, prod_henkilo_id):
    if anonymized_henkilo_id != prod_henkilo_id:
        logger.error(f'Henkilot are not same. Anonymized: {anonymized_henkilo_id}. Prod: {prod_henkilo_id}.')
        sys.exit(5)


def validate_data_is_not_same(anonymized_data, prod_data, henkilo_id):
    """
    Blank values "" can be accepted as same, otherwise same values mean the anonymization has failed.
    """
    hash_of_empty_string = hash_string('')

    if (anonymized_data == '' or anonymized_data == hash_of_empty_string or
            prod_data == '' or prod_data == hash_of_empty_string):
        return None

    if anonymized_data == prod_data:
        logger.error(f'Anonymization has failed for henkilo-id: {henkilo_id}.')
        sys.exit(6)


def validate_henkilo_data(anonymized_henkilo, prod_henkilo):
    """
    Henkilo-id must be same for anonymized and prod -henkilo (otherwise we are not comparing the same henkilo).
    All the rest of the data must be different. Otherwise the anonymization has failed.
    An exception is with blank values "" where we must accept same values.
    """
    prod_henkilo_id = prod_henkilo['id']
    validate_id_is_same(anonymized_henkilo['id'], prod_henkilo_id)
    validate_data_is_not_same(anonymized_henkilo['etunimet'], prod_henkilo['etunimet'], prod_henkilo_id)
    validate_data_is_not_same(anonymized_henkilo['henkilotunnus_unique_hash'],
                              prod_henkilo['henkilotunnus_unique_hash'], prod_henkilo_id)
    validate_data_is_not_same(anonymized_henkilo['katuosoite'], prod_henkilo['katuosoite'], prod_henkilo_id)
    validate_data_is_not_same(anonymized_henkilo['kutsumanimi'], prod_henkilo['kutsumanimi'], prod_henkilo_id)
    validate_data_is_not_same(anonymized_henkilo['sukunimi'], prod_henkilo['sukunimi'], prod_henkilo_id)
    validate_data_is_not_same(anonymized_henkilo['syntyma_pvm'], prod_henkilo['syntyma_pvm'], prod_henkilo_id)


def anonymization_validation(anonymized_data_yhteenveto, prod_data_yhteenveto):
    first_henkilo_anonymized = anonymized_data_yhteenveto['first_henkilo']
    first_henkilo_prod = prod_data_yhteenveto['first_henkilo']
    validate_henkilo_data(first_henkilo_anonymized, first_henkilo_prod)

    middle_henkilo_anonymized = anonymized_data_yhteenveto['middle_henkilo']
    middle_henkilo_prod = prod_data_yhteenveto['middle_henkilo']
    validate_henkilo_data(middle_henkilo_anonymized, middle_henkilo_prod)

    last_henkilo_anonymized = anonymized_data_yhteenveto['last_henkilo']
    last_henkilo_prod = prod_data_yhteenveto['last_henkilo']
    validate_henkilo_data(last_henkilo_anonymized, last_henkilo_prod)


def main():
    """
    If validation is OK, exit with sys.exit(0)
    Else, exit program with non-zero exit code.
    """
    check_environment_variables()
    anonymisointi_yhteenveto_api = '/api/admin/anonymisointi-yhteenveto/'

    anonymized_data_yhteenveto = get_request(anonymisointi_yhteenveto_api, prod=False)
    basic_anonymization_validation(anonymized_data_yhteenveto)

    first_henkilo_id = anonymized_data_yhteenveto['first_henkilo']['id']
    middle_henkilo_id = anonymized_data_yhteenveto['middle_henkilo']['id']
    last_henkilo_id = anonymized_data_yhteenveto['last_henkilo']['id']

    query_params = f'?first_henkilo_id={first_henkilo_id}&' \
                   f'middle_henkilo_id={middle_henkilo_id}&' \
                   f'last_henkilo_id={last_henkilo_id}'

    prod_yhteenveto_api_with_query_params = f'{anonymisointi_yhteenveto_api}{query_params}'
    prod_data_yhteenveto = get_request(prod_yhteenveto_api_with_query_params, prod=True)

    anonymization_validation(anonymized_data_yhteenveto, prod_data_yhteenveto)


if __name__ == '__main__':
    main()
