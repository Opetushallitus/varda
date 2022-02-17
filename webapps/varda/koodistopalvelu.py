import datetime
import logging

from django.db.models import Q

from varda.cache import delete_cache_keys_related_model
from varda.clients import koodistopalvelu_client
from varda.enums.koodistot import Koodistot
from varda.models import Z2_Koodisto, Z2_CodeTranslation, Z2_Code

logger = logging.getLogger(__name__)
KOODISTOPALVELU_DICT = {
    Koodistot.kunta_koodit: 'kunta',
    Koodistot.kieli_koodit: 'kielikoodistoopetushallinto',
    Koodistot.jarjestamismuoto_koodit: 'vardajarjestamismuoto',
    Koodistot.toimintamuoto_koodit: 'vardatoimintamuoto',
    Koodistot.kasvatusopillinen_jarjestelma_koodit: 'vardakasvatusopillinenjarjestelma',
    Koodistot.toiminnallinen_painotus_koodit: 'vardatoiminnallinenpainotus',
    Koodistot.tyosuhde_koodit: 'vardatyosuhde',
    Koodistot.tyoaika_koodit: 'vardatyoaika',
    Koodistot.tehtavanimike_koodit: 'vardatehtavanimike',
    Koodistot.sukupuoli_koodit: 'sukupuoli',
    Koodistot.tutkinto_koodit: 'vardatutkinto',
    Koodistot.maksun_peruste_koodit: 'vardamaksunperuste',
    Koodistot.lahdejarjestelma_koodit: 'vardalahdejarjestelma',
    Koodistot.postinumero_koodit: 'posti',
    Koodistot.virhe_koodit: 'vardavirheviestit',
    Koodistot.yritysmuoto_koodit: 'yritysmuoto'
}
LANGUAGE_CODES = ['FI', 'SV', 'EN']


def update_koodistot():
    # Check if there are any old koodistot
    old_koodisto_qs = Z2_Koodisto.objects.filter(~Q(name__in=Koodistot.list()))
    if old_koodisto_qs.exists():
        Z2_CodeTranslation.objects.filter(code__koodisto__in=old_koodisto_qs).delete()
        Z2_Code.objects.filter(koodisto__in=old_koodisto_qs).delete()
        old_koodisto_qs.delete()

    for key, value in KOODISTOPALVELU_DICT.items():
        koodisto_result = koodistopalvelu_client.get_koodisto(value)
        if not koodisto_result:
            # Koodistopalvelu response was empty, continue to next koodisto
            logger.warning('Could not get koodisto {} from koodistopalvelu'.format(value))
            continue

        update_datetime = parse_koodistopalvelu_datetime(koodisto_result['paivitysPvm'])
        # Update or create Z2_Koodisto
        koodisto_obj = Z2_Koodisto.objects.update_or_create(name=key.value,
                                                            defaults={'name_koodistopalvelu': value,
                                                                      'version': koodisto_result['versio'],
                                                                      'update_datetime': update_datetime})[0]

        code_list = koodistopalvelu_client.get_koodisto_codes(value)
        if not code_list:
            # Koodistopalvelu response was empty, continue to next koodisto
            logger.warning('Could not get koodisto {} codes from koodistopalvelu'.format(value))
            continue

        new_code_list = []
        for code in code_list:
            new_code_list.append(code['koodiArvo'])
            code_obj, created = Z2_Code.objects.update_or_create(koodisto=koodisto_obj, code_value=code['koodiArvo'],
                                                                 defaults={'alkamis_pvm': code['voimassaAlkuPvm'],
                                                                           'paattymis_pvm': code['voimassaLoppuPvm']})

            new_translation_list = []
            for translation in code['metadata']:
                new_translation_list.append(translation['kieli'])

                translation_name = translation['nimi'] or ''
                translation_description = translation['kuvaus'] or ''
                translation_short_name = translation['lyhytNimi'] or ''
                Z2_CodeTranslation.objects.update_or_create(code=code_obj, language=translation['kieli'],
                                                            defaults={'name': translation_name,
                                                                      'description': translation_description,
                                                                      'short_name': translation_short_name})

            # Check if there are any old translations
            old_translation_qs = Z2_CodeTranslation.objects.filter(Q(code=code_obj) &
                                                                   ~Q(language__in=new_translation_list))
            old_translation_qs.delete()

        # Check if there are any old codes
        old_code_qs = Z2_Code.objects.filter(Q(koodisto=koodisto_obj) & ~Q(code_value__in=new_code_list))
        if old_code_qs.exists():
            Z2_CodeTranslation.objects.filter(code__in=old_code_qs).delete()
            old_code_qs.delete()

    delete_koodisto_cache()


def parse_koodistopalvelu_datetime(input_datetime):
    # In testiopintopolku koodistopalvelu paivitysPvm is date-string, in opintopolku koodistopalvelu it's timestamp
    if isinstance(input_datetime, int):
        # datetime.fromtimestamp takes seconds, koodistopalvelu has milliseconds
        result_datetime = datetime.datetime.fromtimestamp(input_datetime / 1000, datetime.timezone.utc)
    else:
        result_datetime = datetime.datetime.strptime(input_datetime, '%Y-%m-%d')
        result_datetime = result_datetime.replace(tzinfo=datetime.timezone.utc)
    return result_datetime


def delete_koodisto_cache():
    for language in LANGUAGE_CODES:
        delete_cache_keys_related_model('koodistot', language)
