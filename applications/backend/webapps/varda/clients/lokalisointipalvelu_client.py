from varda.misc import get_json_from_external_service

SERVICE_NAME = "lokalisointi"
LOKALISOINTI_URL_FORMAT = "/cxf/rest/v1/localisation?category={0}&locale={1}"
LOKALISOINTI_URL_FORMAT_NO_LOCALE = "/cxf/rest/v1/localisation?category={}"


def get_lokalisointi(category, locale):
    if locale:
        url = LOKALISOINTI_URL_FORMAT.format(category, locale)
    else:
        url = LOKALISOINTI_URL_FORMAT_NO_LOCALE.format(category)

    result = get_json_from_external_service(SERVICE_NAME, url, auth=False)
    result_data = None
    if result["is_ok"]:
        result_data = result["json_msg"]

    return result_data
