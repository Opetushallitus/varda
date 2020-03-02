import json
import logging
import requests

from django.conf import settings

from varda.enums.ytj import YtjYritysmuoto
from varda.misc import get_json_from_external_service, post_json_to_external_service, put_json_to_external_service

logger = logging.getLogger(__name__)
SERVICE_NAME = 'organisaatio-service'
ORGANISAATIOPALVELU_API_V2 = '/rest/organisaatio/v2/'
ORGANISAATIOPALVELU_API_V4 = '/rest/organisaatio/v4/'


def get_organisaatiopalvelu_info(organisaatio_oid):
    url = settings.OPINTOPOLKU_DOMAIN + '/' + SERVICE_NAME + ORGANISAATIOPALVELU_API_V4 + organisaatio_oid
    result_info = {'result_ok': False}
    try:
        r = requests.get(url)
        response = json.loads(r.content)
    except (requests.exceptions.RequestException, json.decoder.JSONDecodeError) as e:
        logger.error(e)
        return result_info
    except ValueError as e:
        logger.error('Url: {}, Error: {}'.format(url, e))
        return result_info
    if not response:
        return result_info
    return _parse_organisaatio_data(response, organisaatio_oid)


def _parse_organisaatio_data(response, organisaatio_oid):
    if 'ytjkieli' in response:
        try:
            kieli = response['ytjkieli'].split('_')[1].split('#')[0]
        except IndexError:
            kieli = 'fi'
    else:
        kieli = 'fi'  # current default value
    nimi = response['nimi'][kieli]
    kayntios = response['kayntiosoite']
    postios = response['postiosoite']
    try:
        return {
            'result_ok': True,
            'nimi': nimi,
            'ytunnus': response.get('ytunnus', ''),
            'organisaatio_oid': response['oid'],
            'kunta_koodi': response['kotipaikkaUri'].split('_')[1],
            'kayntiosoite': kayntios['osoite'],
            'kayntiosoite_postinumero': kayntios['postinumeroUri'].split('_')[1],
            'kayntiosoite_postitoimipaikka': kayntios['postitoimipaikka'],
            'postiosoite': postios['osoite'],
            'postinumero': postios['postinumeroUri'].split('_')[1],
            'postitoimipaikka': postios['postitoimipaikka'],
            'ytjkieli': kieli,
            'yritysmuoto': YtjYritysmuoto(response.get('yritysmuoto', 'Ei yritysmuotoa')).name,
            'alkamis_pvm': response['alkuPvm'],
            'paattymis_pvm': response.get('lakkautusPvm', '')
        }
    except (KeyError, ValueError) as e:
        logger.error('Could not parse organisaatio data for vakajarjestaja {} with cause {}'
                     .format(organisaatio_oid, e))
    return {'result_ok': False}


def get_parent_oid(child_oid):
    organisaatio_url = ORGANISAATIOPALVELU_API_V4 + 'hae?aktiiviset=true&oid=' + child_oid
    reply_msg = get_json_from_external_service(SERVICE_NAME, organisaatio_url, auth=False)
    if not reply_msg['is_ok']:
        return None

    reply_json = reply_msg['json_msg']

    if 'numHits' not in reply_json or ('numHits' in reply_json and reply_json['numHits'] != 1):
        logger.warning('No organization hit for: /' + SERVICE_NAME + organisaatio_url)
        return None

    try:
        organization_data = reply_json['organisaatiot'][0]
    except IndexError:
        logger.error('IndexError with organization: /' + SERVICE_NAME + organisaatio_url)
        return None

    if 'parentOid' not in organization_data:
        logger.error('Problem with parentOid: /' + SERVICE_NAME + organisaatio_url)
        return None
    else:
        return organization_data['parentOid']


def organization_is_not_active_vaka_organization(organisaatio_oid, must_be_vakajarjestaja=False):
    """
    We need to exclude the organizations which don't have a label
    'Varhaiskasvatuksen jarjestaja',  i.e. 'organisaatiotyyppi_07' or
    'Varhaiskasvatuksen toimipaikka', i.e. 'organisaatiotyyppi_08'
    Ref: https://github.com/Opetushallitus/organisaatio/blob/master/organisaatio-service/src/main/resources/db/migration/V084__organisaatio_tyypit.sql

    If you need to check explicitly that the organization is not 'Varhaiskasvatuksen jarjestaja', set the must_be_vakajarjestaja to True.
    """
    organisaatio_url = ORGANISAATIOPALVELU_API_V4 + 'hae?aktiiviset=true&oid=' + organisaatio_oid
    reply_msg = get_json_from_external_service(SERVICE_NAME, organisaatio_url, auth=False)
    if not reply_msg['is_ok']:
        return True

    reply_json = reply_msg['json_msg']

    if 'numHits' not in reply_json or ('numHits' in reply_json and reply_json['numHits'] != 1):
        if organisaatio_oid != settings.OPETUSHALLITUS_ORGANISAATIO_OID:
            logger.warning('No organization hit for: /' + SERVICE_NAME + organisaatio_url)
        return True

    try:
        organization_data = reply_json['organisaatiot'][0]
    except IndexError:
        logger.error('Problem with organization: /' + SERVICE_NAME + organisaatio_url)
        return None
    if 'organisaatiotyypit' not in organization_data or 'status' not in organization_data:
        logger.error('Organisaatio missing rquired data: /' + SERVICE_NAME + organisaatio_url)
        return True
    return is_not_active(organization_data, must_be_vakajarjestaja)


def is_not_active(organization_data, must_be_vakajarjestaja=False):
    if 'organisaatiotyypit' not in organization_data and 'tyypit' not in organization_data or 'status' not in organization_data:
        logger.error('Organisaatio missing rquired data: {}'.format(organization_data['oid']))
        return True
    if not is_of_type(organization_data, 'organisaatiotyyppi_07', 'organisaatiotyyppi_08'):
        return True

    if must_be_vakajarjestaja and not is_of_type(organization_data, 'organisaatiotyyppi_07'):
        return True

    if organization_data['status'] == 'AKTIIVINEN':
        return False  # This is expected result
    else:
        logger.error('Organisaatio status not AKTIIVINEN: {}'.format(organization_data['oid']))
        return True


def is_active(organization_data, must_be_vakajarjestaja=False):
    return not is_not_active(organization_data, must_be_vakajarjestaja)


def is_of_type(organisation_data, *args):
    organisation_types = organisation_data.get('tyypit', []) + organisation_data.get('organisaatiotyypit', [])
    return any(org_type in args for org_type in organisation_types)


def organization_is_vakajarjestaja(organisaatio_oid):
    organisaatio_url = ORGANISAATIOPALVELU_API_V4 + 'hae?aktiiviset=true&oid=' + organisaatio_oid
    reply_msg = get_json_from_external_service(SERVICE_NAME, organisaatio_url, auth=False)
    if not reply_msg['is_ok']:
        return True

    reply_json = reply_msg['json_msg']

    if 'numHits' not in reply_json or ('numHits' in reply_json and reply_json['numHits'] != 1):
        logger.warning('No organization hit for: /' + SERVICE_NAME + organisaatio_url)
        return True

    try:
        organization_data = reply_json['organisaatiot'][0]
    except IndexError:
        logger.error('Problem with organization: /' + SERVICE_NAME + organisaatio_url)
        return None

    if 'organisaatiotyypit' not in organization_data:
        logger.error('Organisaatio missing rquired data: /' + SERVICE_NAME + organisaatio_url)
        return True

    return is_of_type(organization_data, 'organisaatiotyyppi_07')


def is_vakajarjestaja(organisation):
    """
    Different apis return this in different fields. General rule: /organisaatio-service/rest/organisaatio?oid=# returns
    organisaatiotyypit while other apis return tyypit.
    :param organisation: Organisation data
    :return: Is organisation vakajarjestaja
    """
    return is_of_type(organisation, 'organisaatiotyyppi_07')


def check_if_toimipaikka_exists_by_name(toimipaikka_name, parent_oid):
    """
    Check from organisaatiopalvelu if there already exists a toimipaikka with the given name,
    under the given vakajarjestaja (i.e. parent_oid). Returns result of the search (True or False),
    and oid's of the matching names (if any).
    In organisaatiopalvelu, search by name is of type 'contains', so there can be multiple results
    in the initial search.

    If something fails, we send logs, and return True <-> We do not want to let user POST a new toimipaikka when there were errors.
    """
    http_url_suffix = (ORGANISAATIOPALVELU_API_V4 + 'hae?aktiiviset=true&suunnitellut=true&lakkautetut=true&oidRestrictionList=' +
                       parent_oid + '&organisaatiotyyppi=organisaatiotyyppi_08&searchStr=' + toimipaikka_name)
    reply_msg = get_json_from_external_service(SERVICE_NAME, http_url_suffix, auth=False)

    oids = []
    if not reply_msg['is_ok']:
        return (True, oids)

    reply_json = reply_msg['json_msg']
    match = False

    try:
        for organization in reply_json['organisaatiot']:
            organization_names = [name.lower().strip() for name in organization['nimi'].values()]
            for organisation_name in organization_names:
                if toimipaikka_name.lower().strip() == organisation_name and organization['oid'] not in oids:
                    match = True
                    oids.append(organization['oid'])
    except KeyError:
        logger.error('Organisaatiopalvelu-error: ' + toimipaikka_name + ', ' + parent_oid)
        return (True, [])

    return (match, oids)


def get_organisaatio(organisaatio_oid, internal_id=None):
    """
    Get organisaatio by oid
    :param internal_id: varda database id for organisaatio
    :param organisaatio_oid: organisaatio oid
    :return: json data from organisaatio service
    """
    url_path = ORGANISAATIOPALVELU_API_V4 + organisaatio_oid + '?includeImage=false'
    reply_msg = get_json_from_external_service(SERVICE_NAME, url_path, auth=False)

    if reply_msg['is_ok']:
        return reply_msg['json_msg']

    logger.error('Could not fetch organisaatio-info from Org-palvelu, Id: ' + str(internal_id) + ', oid: ' + organisaatio_oid)
    return None


def create_organisaatio(organisaatio_json):
    expected_status_code = 200  # organisaatiopalvelu returns 200 on successful POSTs
    response = post_json_to_external_service('organisaatio-service', ORGANISAATIOPALVELU_API_V4, organisaatio_json, expected_status_code)
    if response['is_ok']:
        oid = response['json_msg']['organisaatio']['oid']
        return {'toimipaikka_created': True, 'organisaatio_oid': oid}
    else:
        return {'toimipaikka_created': False}


def update_organisaatio(organisaatio_oid, organisaatio_update_json, internal_id=None):
    expected_status_code = 200
    http_url_suffix_put = ORGANISAATIOPALVELU_API_V4 + organisaatio_oid
    response = put_json_to_external_service('organisaatio-service', http_url_suffix_put, organisaatio_update_json, expected_status_code)
    if not response['is_ok']:
        logger.error('Could not update organisaatio in Org-palvelu. Id: ' + str(internal_id) + ', oid: ' + organisaatio_oid)


def get_changed_since(since):
    """
    Get changed organisations after given date time
    :param since: date time from when we want changed organisations
    :return: oids of changed organisations
    """
    # Organisaatio-service formats: 'yyyy-MM-dd', 'yyyy-MM-dd HH:mm'
    formatted_time = since.strftime('%Y-%m-%d %H:%M')
    url_path_query = ORGANISAATIOPALVELU_API_V2 + 'muutetut/oid?lastModifiedSince=' + formatted_time
    result = get_json_from_external_service(SERVICE_NAME, url_path_query, auth=False)
    oids = result['json_msg']['oids']
    return list(filter(lambda oid: oid != '', oids))


def get_multiple_organisaatio(organisaatio_oids):
    """
    Returns all organisations from organisaatio-service that match given oids. Missing ones won't raise error.
    Note: Organisaatio-service allows currently to fetch max. 1000 organisations in single request.
    :param organisaatio_oids: List of organisaatio oids
    :return: list of organisaatio data matching given oids
    """
    if not organisaatio_oids:
        return []
    url_path = ORGANISAATIOPALVELU_API_V4 + 'findbyoids'
    data = json.dumps(list(organisaatio_oids))
    response = post_json_to_external_service('organisaatio-service', url_path, data, 200, auth=False)
    return response['json_msg']
