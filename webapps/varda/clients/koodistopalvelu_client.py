from varda.misc import get_json_from_external_service

SERVICE_NAME = 'koodisto-service'
KOODISTO_URL_FORMAT = '/rest/json/{}'
KOODISTO_CODES_URL_FORMAT = '/rest/json/{}/koodi?onlyValidKoodis=false'


def get_koodisto(koodisto_name):
    result = get_json_from_external_service(SERVICE_NAME, KOODISTO_URL_FORMAT.format(koodisto_name), auth=False)
    result_data = None
    if result['is_ok']:
        result_data = result['json_msg']

    return result_data


def get_koodisto_codes(koodisto_name):
    result = get_json_from_external_service(SERVICE_NAME, KOODISTO_CODES_URL_FORMAT.format(koodisto_name), auth=False)
    result_data = []
    if result['is_ok']:
        result_data = result['json_msg']

    return result_data
