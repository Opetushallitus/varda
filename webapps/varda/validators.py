import datetime
import ipaddress
import re
import decimal
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, CharField
from django.forms.models import model_to_dict
from django.utils.deconstruct import deconstructible
from rest_framework.exceptions import ValidationError

from varda.enums.error_messages import ErrorMessages
from varda.enums.koodistot import Koodistot


def validate_email(email):
    # Taken from https://github.com/Opetushallitus/organisaatio/blob/e708e36bf5d053b4d461257cbedc11420496befd/organisaatio-service/src/main/java/fi/vm/sade/organisaatio/model/Email.java#L37
    # with an exception: domain name must start with [A-Za-z0-9]
    email_regex = re.compile(r'^[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+(\.[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+)*@[A-Za-z0-9][A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*(\.[A-Za-z]{2,})$')
    if not email_regex.fullmatch(email):
        raise ValidationError([ErrorMessages.GE024.value])


def validate_henkilotunnus_or_oid_needed(validated_data):
    if ('henkilotunnus' not in validated_data and 'henkilo_oid' not in validated_data or
            'henkilotunnus' in validated_data and 'henkilo_oid' in validated_data):
        raise ValidationError({'errors': [ErrorMessages.HE004.value]})


def validate_henkilotunnus(henkilotunnus):
    """
    Validate the date, the middle character, and the identification part.
    """
    if len(henkilotunnus) != 11:
        raise ValidationError({'henkilotunnus': [ErrorMessages.HE005.value]})
    day = henkilotunnus[:2]
    month = henkilotunnus[2:4]
    year = henkilotunnus[4:6]
    century = henkilotunnus[6]

    check_tilapainen_hetu(henkilotunnus)
    if century not in ('-', 'A'):
        raise ValidationError({'henkilotunnus': [ErrorMessages.HE006.value]})
    if century == '-':
        cent = '19'
    else:
        cent = '20'
    try:
        birthday = datetime.date(int(cent + year), int(month), int(day))
        delta = datetime.date.today() - birthday
        if delta.days <= 0:
            raise Exception()
    except Exception:
        raise ValidationError({'henkilotunnus': [ErrorMessages.HE007.value]})
    checknumber = henkilotunnus[:6] + henkilotunnus[7:10]
    check = henkilotunnus[10]
    code = '0123456789ABCDEFHJKLMNPRSTUVWXY'
    try:
        remainder = int(checknumber) % 31
        if check != code[remainder]:
            raise Exception()
    except Exception:
        raise ValidationError({'henkilotunnus': [ErrorMessages.HE008.value]})


def check_tilapainen_hetu(henkilotunnus):
    if settings.PRODUCTION_ENV:
        try:
            individual_number = int(henkilotunnus[7:10])
            if individual_number < 2 or individual_number > 899:
                raise Exception()
        except Exception:
            raise ValidationError({'henkilotunnus': [ErrorMessages.HE009.value]})


def validate_kutsumanimi(etunimet, kutsumanimi):
    """
    e.g. Liisa-Marja Tuuli -> valid kutsumanimet: ['liisa-marja', 'liisa', 'marja', 'tuuli']

    First, check that kutsumanimi is one name.
    """
    splitted_kutsumanimi_array = kutsumanimi.split(' ')
    kutsumanimi_array = list(filter(None, splitted_kutsumanimi_array))  # Remove empty, i.e. ''
    if len(kutsumanimi_array) != 1:
        raise ValidationError({'kutsumanimi': [ErrorMessages.HE010.value]})
    validated_kutsumanimi = kutsumanimi_array[0].lower()

    splitted_etunimet_array = etunimet.split(' ')
    etunimet_array = list(filter(None, splitted_etunimet_array))
    etunimet_array_final = etunimet_array

    for etunimi in etunimet_array:
        etunimet_splitted_by_dash_array = etunimi.split('-')
        if len(etunimet_splitted_by_dash_array) > 1:  # Do nothing if name doesn't have "-" in it (to avoid duplicates)
            for nimi in etunimet_splitted_by_dash_array:
                etunimet_array_final.append(nimi)

    for etunimi in etunimet_array_final:
        if etunimi.lower() == validated_kutsumanimi:
            return

    raise ValidationError({'kutsumanimi': [ErrorMessages.HE011.value]})


def validate_postinumero(postinumero):
    """
    Validate the postal code: numeric, length 5 string
    """
    if (len(postinumero) == 5) and postinumero.isnumeric() and postinumero != '00000':
        pass
    else:
        raise ValidationError([ErrorMessages.MI005.value])


def validate_y_tunnus(y_tunnus):
    """
    Validation of y-tunnus: http://tarkistusmerkit.teppovuori.fi/
    """
    if len(y_tunnus) != 9:
        raise ValidationError([ErrorMessages.VJ003.value])
    tunnus = y_tunnus[:7]
    hyphen = y_tunnus[7]
    if hyphen != '-':
        raise ValidationError([ErrorMessages.VJ004.value])
    check = y_tunnus[8]
    multiplier = [7, 9, 10, 5, 8, 4, 2]
    try:
        summa = sum([int(tunnus[i]) * multiplier[i] for i in range(len(tunnus))])
        remainder = summa % 11
        if remainder == 0:
            checknumber = 0
        elif remainder == 1:
            raise ValidationError([ErrorMessages.VJ005.value])
        else:
            checknumber = 11 - remainder
        if checknumber != int(check):
            raise ValidationError([ErrorMessages.VJ006.value])
    except Exception:
        raise ValidationError([ErrorMessages.VJ006.value])


def validate_arrayfield(provided_array):
    if not len(provided_array):
        raise ValidationError([ErrorMessages.GE017.value])


def validate_ipv4_address(ip_address):
    if ip_address:
        try:
            ipaddress.ip_network(ip_address)
        except ValueError:
            raise ValidationError([ErrorMessages.VJ007.value])


def validate_ipv6_address(ip_address):
    if ip_address:
        try:
            ipaddress.ip_network(ip_address)
        except ValueError:
            raise ValidationError([ErrorMessages.VJ008.value])


def validate_koodi_in_general(koodi):
    splitted_koodi = koodi.split(' ')
    if len(splitted_koodi) > 1:
        raise ValidationError([ErrorMessages.KO001.value])
    if not koodi.isalnum():
        raise ValidationError([ErrorMessages.KO002.value])


def validate_z2_koodi(code_value, koodisto_name, alkamis_pvm=None, paattymis_pvm=None, field_name=None,
                      paattymis_pvm_only=True):
    from varda.models import Z2_Koodisto, Z2_Code

    validate_koodi_in_general(code_value)
    koodisto_qs = Z2_Koodisto.objects.filter(name=koodisto_name)
    if koodisto_qs.exists:
        koodi_qs = Z2_Code.objects.filter(koodisto=koodisto_qs.first(), code_value__iexact=code_value)
        if not koodi_qs.exists():
            raise ValidationError([ErrorMessages.KO003.value])
        koodi_instance = koodi_qs.first()

        code_starts_after_start = False if paattymis_pvm_only else (alkamis_pvm and koodi_instance.alkamis_pvm > alkamis_pvm)
        code_ends_before_start = alkamis_pvm and koodi_instance.paattymis_pvm and koodi_instance.paattymis_pvm < alkamis_pvm
        code_ends_before_end = paattymis_pvm and koodi_instance.paattymis_pvm and koodi_instance.paattymis_pvm < paattymis_pvm

        if code_starts_after_start or code_ends_before_start or code_ends_before_end:
            raise ValidationError({field_name: [ErrorMessages.KO005.value]})
    else:
        raise ValidationError([ErrorMessages.KO004.value])


def validate_maksun_peruste_koodi(maksun_peruste_koodi, alkamis_pvm=None, paattymis_pvm=None,
                                  field_name='maksun_peruste_koodi'):
    validate_z2_koodi(maksun_peruste_koodi, Koodistot.maksun_peruste_koodit.value, alkamis_pvm, paattymis_pvm,
                      field_name)


def validate_kunta_koodi(kunta_koodi, alkamis_pvm=None, paattymis_pvm=None, field_name='kunta_koodi'):
    validate_z2_koodi(kunta_koodi, Koodistot.kunta_koodit.value, alkamis_pvm, paattymis_pvm, field_name)


def validate_jarjestamismuoto_koodi(jarjestamismuoto_koodi, alkamis_pvm=None, paattymis_pvm=None,
                                    field_name='jarjestamismuoto_koodi'):
    validate_z2_koodi(jarjestamismuoto_koodi, Koodistot.jarjestamismuoto_koodit.value, alkamis_pvm, paattymis_pvm,
                      field_name)


def validate_toimintamuoto_koodi(toimintamuoto_koodi, alkamis_pvm=None, paattymis_pvm=None,
                                 field_name='toimintamuoto_koodi'):
    validate_z2_koodi(toimintamuoto_koodi, Koodistot.toimintamuoto_koodit.value, alkamis_pvm, paattymis_pvm, field_name)


def validate_kasvatusopillinen_jarjestelma_koodi(kasvatusopillinen_jarjestelma_koodi, alkamis_pvm=None,
                                                 paattymis_pvm=None, field_name='kasvatusopillinen_jarjestelma_koodi'):
    validate_z2_koodi(kasvatusopillinen_jarjestelma_koodi, Koodistot.kasvatusopillinen_jarjestelma_koodit.value,
                      alkamis_pvm, paattymis_pvm, field_name)


def validate_toimintapainotus_koodi(toimintapainotus_koodi, alkamis_pvm=None, paattymis_pvm=None,
                                    field_name='toimintapainotus_koodi'):
    validate_z2_koodi(toimintapainotus_koodi, Koodistot.toiminnallinen_painotus_koodit.value, alkamis_pvm,
                      paattymis_pvm, field_name)


def validate_tyosuhde_koodi(tyosuhde_koodi, alkamis_pvm=None, paattymis_pvm=None, field_name='tyosuhde_koodi'):
    validate_z2_koodi(tyosuhde_koodi, Koodistot.tyosuhde_koodit.value, alkamis_pvm, paattymis_pvm, field_name)


def validate_tyoaika_koodi(tyoaika_koodi, alkamis_pvm=None, paattymis_pvm=None, field_name='tyoaika_koodi'):
    validate_z2_koodi(tyoaika_koodi, Koodistot.tyoaika_koodit.value, alkamis_pvm, paattymis_pvm, field_name)


def validate_tehtavanimike_koodi(tehtavanimike_koodi, alkamis_pvm=None, paattymis_pvm=None,
                                 field_name='tehtavanimike_koodi'):
    validate_z2_koodi(tehtavanimike_koodi, Koodistot.tehtavanimike_koodit.value, alkamis_pvm, paattymis_pvm, field_name)


def validate_kieli_koodi(kieli_koodi, alkamis_pvm=None, paattymis_pvm=None, field_name=None):
    validate_z2_koodi(kieli_koodi, Koodistot.kieli_koodit.value, alkamis_pvm, paattymis_pvm, field_name)


def validate_sukupuoli_koodi(sukupuoli_koodi, alkamis_pvm=None, paattymis_pvm=None, field_name='sukupuoli_koodi'):
    validate_z2_koodi(sukupuoli_koodi, Koodistot.sukupuoli_koodit.value, alkamis_pvm, paattymis_pvm, field_name)


def validate_tutkinto_koodi(tutkinto_koodi, alkamis_pvm=None, paattymis_pvm=None, field_name='tutkinto_koodi'):
    validate_z2_koodi(tutkinto_koodi, Koodistot.tutkinto_koodit.value, alkamis_pvm, paattymis_pvm, field_name)


def validate_lahdejarjestelma_koodi(lahdejarjestelma_koodi, alkamis_pvm=None, paattymis_pvm=None,
                                    field_name='lahdejarjestelma'):
    validate_z2_koodi(lahdejarjestelma_koodi, Koodistot.lahdejarjestelma_koodit.value, alkamis_pvm, paattymis_pvm,
                      field_name)


def validate_yritysmuoto_koodi(yritysmuoto_koodi, alkamis_pvm=None, paattymis_pvm=None, field_name='yritysmuoto'):
    validate_z2_koodi(yritysmuoto_koodi, Koodistot.yritysmuoto_koodit.value, alkamis_pvm, paattymis_pvm, field_name)


def validate_kieli_koodi_array(kieli_koodi):
    pass


def validate_tutkintonimike_koodi(tutkintonimike_koodi):
    """
    Not in use but referenced in 0001 migration.
    """
    return None


def validate_tyotehtava_koodi(tyotehtava_koodi):
    """
    Not in use but referenced in 0001 migration.
    """
    return None


def validate_IBAN_koodi(IBAN_koodi):
    try:
        IBAN = IBAN_koodi.replace(' ', '')
        if len(IBAN) != 18:
            raise ValidationError([ErrorMessages.VJ009.value])
        if IBAN[:2].lower() != 'fi':
            raise ValidationError([ErrorMessages.VJ009.value])
        IBA = IBAN[4:] + '1518' + IBAN[2:4]
        check = int(IBA) % 97
        if check != 1:
            raise ValidationError([ErrorMessages.VJ009.value])
    except (TypeError, ValueError, DjangoValidationError):
        raise ValidationError([ErrorMessages.VJ009.value])


def validate_puhelinnumero(puhelinnumero):
    puhelinnumero = puhelinnumero.replace('-', '')
    puhelinnumero = puhelinnumero.replace(' ', '')
    if not puhelinnumero:
        raise ValidationError([ErrorMessages.GE001.value])
    puhelinnumero_regex = re.compile(r'^(\+358)[1-9][0-9]{5,10}')
    if not puhelinnumero_regex.fullmatch(puhelinnumero):
        raise ValidationError([ErrorMessages.MI006.value])


def parse_paivamaara(paivamaara, default=None):
    if not isinstance(paivamaara, datetime.date):
        if isinstance(paivamaara, str):
            return datetime.datetime.strptime(paivamaara.replace('-', ''), '%Y%m%d').date()
        else:
            return default
    return paivamaara


def validate_paivamaara1_before_paivamaara2(paivamaara1, paivamaara2, can_be_same=False):
    paivamaara1 = parse_paivamaara(paivamaara1, datetime.date(2000, 1, 1))
    paivamaara2 = parse_paivamaara(paivamaara2, datetime.date(2100, 1, 1))

    if paivamaara1 > paivamaara2 or (paivamaara1 == paivamaara2 and not can_be_same):
        return False
    else:
        return True


def validate_paivamaara1_after_paivamaara2(paivamaara1, paivamaara2, can_be_same=False):
    return not validate_paivamaara1_before_paivamaara2(paivamaara1, paivamaara2, not can_be_same)


def validate_paattymispvm_same_or_after_alkamispvm(validated_data):
    """
    If given, validate that the paattymispvm is after alkamispvm.
    (Should a model have this date, they are always called the same by convention.)

    :param validated_data: Django serializer validated data
    """

    if 'paattymis_pvm' in validated_data and validated_data['paattymis_pvm'] is not None:
        if not validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm'], can_be_same=True):
            msg = {'paattymis_pvm': [ErrorMessages.MI004.value]}
            raise ValidationError(msg)


def validate_vaka_paattymis_pvm(is_yksityinen, paattymis_pvm):
    """
    Check that paattymis_pvm is after a certain date, different for yksityinen and kunnallinen Lapsi.
    :param is_yksityinen: True if Lapsi is yksityinen, else False (kunnallinen)
    :param paattymis_pvm: date
    :return: raise error if paattymis_pvm is not valid
    """
    if is_yksityinen:
        paattymis_pvm_limit = datetime.date(2020, 1, 1)
        paattymis_pvm_error = ErrorMessages.MI020.value
    else:
        paattymis_pvm_limit = datetime.date(2019, 1, 1)
        paattymis_pvm_error = ErrorMessages.MI021.value
    if paattymis_pvm and paattymis_pvm < paattymis_pvm_limit:
        raise ValidationError({'paattymis_pvm': [paattymis_pvm_error]})


def validate_dates_within_toimipaikka(validated_data, toimipaikka_obj):
    """
    Check validity of user-submitted toiminnallinenpainotus dates against toimipaikka dates.
    """
    if 'alkamis_pvm' in validated_data:
        if not validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], toimipaikka_obj.paattymis_pvm):
            raise ValidationError({'alkamis_pvm': [ErrorMessages.TP010.value]})
        if not validate_paivamaara1_after_paivamaara2(validated_data['alkamis_pvm'], toimipaikka_obj.alkamis_pvm, can_be_same=True):
            raise ValidationError({'alkamis_pvm': [ErrorMessages.TP011.value]})
    if 'paattymis_pvm' in validated_data:
        if not validate_paivamaara1_before_paivamaara2(validated_data['paattymis_pvm'], toimipaikka_obj.paattymis_pvm, can_be_same=True):
            raise ValidationError({'paattymis_pvm': [ErrorMessages.TP012.value]})


def validate_oid(oid, field_name):
    oid_sections = oid.split('.')
    if len(oid_sections) != 6:
        raise ValidationError({field_name: [ErrorMessages.MI007.value]})
    oph_part = '.'.join(oid_sections[:4])
    identifier = oid_sections[-1]
    if oph_part != '1.2.246.562':
        raise ValidationError({field_name: [ErrorMessages.MI008.value]})
    oidpattern = re.compile('^[1-9]{1}[0-9]{10,21}$')
    if not oidpattern.match(identifier):
        raise ValidationError({field_name: [ErrorMessages.MI009.value]})


def validate_organisaatio_oid(oid):
    field_name = 'organisaatio_oid'
    validate_oid(oid, field_name)
    oid_sections = oid.split('.')
    if oid_sections[4] != '10':
        raise ValidationError({field_name: [ErrorMessages.MI010.value]})


def validate_henkilo_oid(oid):
    field_name = 'henkilo_oid'
    validate_oid(oid, field_name)
    oid_sections = oid.split('.')
    if oid_sections[4] != '24':
        raise ValidationError({field_name: [ErrorMessages.MI011.value]})


def validate_nimi(nimi):
    if not bool(re.match("^[a-zà-öø-ÿåäöÅÄÖA-ZÀ-ÖØ-ß',-.`´*/ ]+$", nimi)):
        raise ValidationError([ErrorMessages.HE012.value])
    if nimi.startswith('-') or nimi.endswith('-') or '--' in nimi:
        raise ValidationError([ErrorMessages.HE013.value])


def validate_toimipaikan_nimi(toimipaikan_nimi):
    special_characters_partial = ['/', '&', '’', '\'', '`', '´', '+', '-', ',', '(']  # Allow toimipaikan nimi to end with '.' and ')'
    special_characters_full = special_characters_partial + ['.', ')']

    # Important to have dash "-" in the end of the regex below
    toimipaikan_nimi_clean = re.sub(r'[/&’\'`´+(),.-]', '', toimipaikan_nimi)
    if not toimipaikan_nimi_clean.replace(' ', '').isalnum():
        raise ValidationError({'nimi': [ErrorMessages.TP013.value]})

    # Checking for name length (min 2)
    if len(toimipaikan_nimi) < 2:
        raise ValidationError({'nimi': [ErrorMessages.TP014.value]})

    # Checking for consecutive repeating special characters (max 2)
    toimipaikan_nimi_simple = re.sub(r'[/&’\'`´+(),.-]', '0', toimipaikan_nimi)
    if '000' in toimipaikan_nimi_simple:
        raise ValidationError({'nimi': [ErrorMessages.TP015.value]})

    if (toimipaikan_nimi.startswith(tuple(special_characters_full)) or
            toimipaikan_nimi.endswith(tuple(special_characters_partial)) or
            '  ' in toimipaikan_nimi):
        raise ValidationError({'nimi': [ErrorMessages.TP016.value]})


def validate_tunniste(tunniste):
    # Validate that tunniste is not hetu
    is_hetu = True
    try:
        validate_henkilotunnus(tunniste)
    except ValidationError:
        is_hetu = False

    # Validate allowed characters
    pattern = re.compile(r'[a-zA-Z0-9.\-_]+')
    is_valid_characters = pattern.fullmatch(tunniste)

    if is_hetu or not is_valid_characters:
        raise ValidationError([ErrorMessages.MI012.value])


def validate_vaka_date(date):
    date_limit = datetime.date(2000, 1, 1)
    if not validate_paivamaara1_after_paivamaara2(date, date_limit, can_be_same=True):
        raise ValidationError([ErrorMessages.MI014.value])


def validate_taydennyskoulutus_suoritus_pvm(date):
    date_limit = datetime.date(2020, 9, 1)
    if not validate_paivamaara1_after_paivamaara2(date, date_limit, can_be_same=True):
        raise ValidationError([ErrorMessages.TK015.value])


def validate_palvelussuhde_paattymis_pvm(date):
    date_limit = datetime.date(2020, 9, 1)
    if not validate_paivamaara1_after_paivamaara2(date, date_limit, can_be_same=True):
        raise ValidationError([ErrorMessages.PS007.value])


def validate_pidempi_poissaolo_paattymis_pvm(date):
    date_limit = datetime.date(2020, 9, 1)
    if not validate_paivamaara1_after_paivamaara2(date, date_limit, can_be_same=True):
        raise ValidationError([ErrorMessages.PP008.value])


@deconstructible
class create_validate_decimal_steps:
    def __init__(self, stepsize):
        if not isinstance(stepsize, decimal.Decimal):
            stepsize = decimal.Decimal(stepsize)
        self.stepsize = stepsize

    def __call__(self, value):
        if value % self.stepsize != 0:
            raise ValidationError([ErrorMessages.GE018.value])

    def __eq__(self, other):
        return self.stepsize == other.stepsize


def fill_missing_fields_for_validations(data, instance):
    """
    Fills patch request fields from instance data to handle validations
    :param data: user input
    :param instance: instance that is being updated
    :return:
    """
    instance_dictionary = model_to_dict(instance)
    excluded_fields = ('muutos_pvm',)
    for field in instance_dictionary:
        if field not in data and field not in excluded_fields:
            data[field] = getattr(instance, field)


def validate_instance_uniqueness(model, data, error, instance_id=None, ignore_fields=()):
    """
    Function that validates that the data is unique withing the provided model.
    :param model: Model class
    :param data: dict of data
    :param error: error message
    :param instance_id: existing instance ID
    :param ignore_fields: Model specific fields that are excluded in validation
    """
    ignore_fields_list = (('id', 'lahdejarjestelma', 'tunniste', 'luonti_pvm', 'muutos_pvm',) +
                          ignore_fields)
    qs_filter = Q()
    for model_field in model._meta.get_fields():
        if model_field.name not in ignore_fields_list and model_field.many_to_one is not False:
            # Only include fields which are not in ignore_fields_list and are not related fields from other models
            # (e.g. Varhaiskasvatuspaatos has varhaiskasvatussuhteet-field, we do not want to include it in validation)
            if isinstance(model_field, CharField):
                # Use iexact lookup in string comparisons
                lookup_expr = '__iexact'
            else:
                lookup_expr = ''
            qs_filter &= Q(**{f'{model_field.name}{lookup_expr}': data.get(model_field.name, None)})

    if instance_id:
        qs_filter &= ~Q(id=instance_id)

    if model.objects.filter(qs_filter).exists():
        raise ValidationError({'errors': [error]})


def validate_alkamis_pvm_before_paattymis_pvm(data):
    alkamis_pvm = data['alkamis_pvm']
    paattymis_pvm = data.get('paattymis_pvm', None)

    if paattymis_pvm and not validate_paivamaara1_before_paivamaara2(alkamis_pvm, paattymis_pvm):
        raise ValidationError({'paattymis_pvm': [ErrorMessages.MI003.value]})


def validate_nested_list_with_two_ints(merge_list):
    if not isinstance(merge_list, list):
        raise TypeError('Invalid list, please check the format')

    for unit in merge_list:
        if not isinstance(unit, list):
            raise TypeError('List is not a list of lists, please check the input format')
        if len(unit) != 2 or not isinstance(unit[0], int) or not isinstance(unit[1], int):
            raise TypeError(f'List length is not equal to two or contains non-integer values {unit}')


def validate_kela_api_datetimefield(field, now, name):
    # Data can be fetched up to a maximum of 1 year ago
    if field:
        try:
            datetime_format = '%Y-%m-%dT%H:%M:%S.%f%z' if '.' in field else '%Y-%m-%dT%H:%M:%S%z'
            field = datetime.datetime.strptime(field, datetime_format)
        except ValueError:
            raise ValidationError({name: [ErrorMessages.GE020.value]})
        if (now.date() - field.date()).days > 365:
            raise ValidationError({name: [ErrorMessages.GE019.value]})
    else:
        field = now - datetime.timedelta(days=7)
    return field
