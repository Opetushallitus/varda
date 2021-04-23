import datetime
import ipaddress
import re
import decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q, CharField
from django.forms.models import model_to_dict
from django.utils.deconstruct import deconstructible
from rest_framework.exceptions import ValidationError as ValidationErrorRest

from varda.enums.error_messages import ErrorMessages
from varda.enums.koodistot import Koodistot

"""
Taken from:
https://github.com/Opetushallitus/organisaatio/blob/e708e36bf5d053b4d461257cbedc11420496befd/organisaatio-service/src/main/java/fi/vm/sade/organisaatio/model/Email.java#L37

With an exception: domain name must start with [A-Za-z0-9]
"""
email_regex = ('^[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+(\\.[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+)*@[A-Za-z0-9][A-Za-z0-9-]+'
               '(\\.[A-Za-z0-9-]+)*(\\.[A-Za-z]{2,})$')


def validate_email(email):
    RegexValidator(regex=email_regex, message=email + ' : Not a valid email address.')(email)


def validate_henkilotunnus_or_oid_needed(validated_data):
    if ('henkilotunnus' not in validated_data and 'henkilo_oid' not in validated_data or
            'henkilotunnus' in validated_data and 'henkilo_oid' in validated_data):
        raise ValidationErrorRest({'errors': [ErrorMessages.HE004.value]})


def validate_henkilotunnus(henkilotunnus):
    """
    Validate the date, the middle character, and the identification part.
    """
    if len(henkilotunnus) != 11:
        raise ValidationErrorRest({'henkilotunnus': [ErrorMessages.HE005.value]})
    day = henkilotunnus[:2]
    month = henkilotunnus[2:4]
    year = henkilotunnus[4:6]
    century = henkilotunnus[6]

    check_tilapainen_hetu(henkilotunnus)
    if century not in ('-', 'A'):
        raise ValidationErrorRest({'henkilotunnus': [ErrorMessages.HE006.value]})
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
        raise ValidationErrorRest({'henkilotunnus': [ErrorMessages.HE007.value]})
    checknumber = henkilotunnus[:6] + henkilotunnus[7:10]
    check = henkilotunnus[10]
    code = '0123456789ABCDEFHJKLMNPRSTUVWXY'
    try:
        remainder = int(checknumber) % 31
        if check != code[remainder]:
            raise Exception()
    except Exception:
        raise ValidationErrorRest({'henkilotunnus': [ErrorMessages.HE008.value]})


def check_tilapainen_hetu(henkilotunnus):
    if settings.PRODUCTION_ENV:
        try:
            individual_number = int(henkilotunnus[7:10])
            if individual_number < 2 or individual_number > 899:
                raise Exception()
        except Exception:
            raise ValidationErrorRest({'henkilotunnus': [ErrorMessages.HE009.value]})


def validate_kutsumanimi(etunimet, kutsumanimi):
    """
    e.g. Liisa-Marja Tuuli -> valid kutsumanimet: ['liisa-marja', 'liisa', 'marja', 'tuuli']

    First, check that kutsumanimi is one name.
    """
    splitted_kutsumanimi_array = kutsumanimi.split(' ')
    kutsumanimi_array = list(filter(None, splitted_kutsumanimi_array))  # Remove empty, i.e. ''
    if len(kutsumanimi_array) != 1:
        raise ValidationErrorRest({'kutsumanimi': [ErrorMessages.HE010.value]})
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

    raise ValidationErrorRest({'kutsumanimi': [ErrorMessages.HE011.value]})


def validate_postinumero(postinumero):
    """
    Validate the postal code: numeric, length 5 string
    """
    if (len(postinumero) == 5) and postinumero.isnumeric() and postinumero != '00000':
        pass
    else:
        raise ValidationErrorRest([ErrorMessages.MI005.value])


def validate_y_tunnus(y_tunnus):
    """
    Validation of y-tunnus: http://tarkistusmerkit.teppovuori.fi/
    """
    if len(y_tunnus) != 9:
        raise ValidationErrorRest([ErrorMessages.VJ003.value])
    tunnus = y_tunnus[:7]
    hyphen = y_tunnus[7]
    if hyphen != '-':
        raise ValidationErrorRest([ErrorMessages.VJ004.value])
    check = y_tunnus[8]
    multiplier = [7, 9, 10, 5, 8, 4, 2]
    try:
        summa = sum([int(tunnus[i]) * multiplier[i] for i in range(len(tunnus))])
        remainder = summa % 11
        if remainder == 0:
            checknumber = 0
        elif remainder == 1:
            raise ValidationErrorRest([ErrorMessages.VJ005.value])
        else:
            checknumber = 11 - remainder
        if checknumber != int(check):
            raise ValidationErrorRest([ErrorMessages.VJ006.value])
    except Exception:
        raise ValidationErrorRest([ErrorMessages.VJ006.value])


def validate_arrayfield(provided_array):
    if not len(provided_array):
        raise ValidationErrorRest([ErrorMessages.GE017.value])


def validate_ipv4_address(ip_address):
    if ip_address:
        try:
            ipaddress.ip_network(ip_address)
        except ValueError:
            raise ValidationErrorRest([ErrorMessages.VJ007.value])


def validate_ipv6_address(ip_address):
    if ip_address:
        try:
            ipaddress.ip_network(ip_address)
        except ValueError:
            raise ValidationErrorRest([ErrorMessages.VJ008.value])


def validate_koodi_in_general(koodi):
    splitted_koodi = koodi.split(' ')
    if len(splitted_koodi) > 1:
        raise ValidationErrorRest([ErrorMessages.KO001.value])
    if not koodi.isalnum():
        raise ValidationErrorRest([ErrorMessages.KO002.value])


def validate_z2_koodi(koodi, field_name):
    from varda.models import Z2_Koodisto, Z2_Code

    validate_koodi_in_general(koodi)
    koodisto_qs = Z2_Koodisto.objects.filter(name=field_name)
    if koodisto_qs.exists:
        koodi_qs = Z2_Code.objects.filter(koodisto=koodisto_qs.first(), code_value__iexact=koodi)
        if not koodi_qs.exists():
            raise ValidationErrorRest([ErrorMessages.KO003.value])
    else:
        raise ValidationErrorRest([ErrorMessages.KO004.value])


def validate_maksun_peruste_koodi(maksun_peruste_koodi):
    validate_z2_koodi(maksun_peruste_koodi, Koodistot.maksun_peruste_koodit.value)


def validate_kunta_koodi(kunta_koodi):
    validate_z2_koodi(kunta_koodi, Koodistot.kunta_koodit.value)


def validate_jarjestamismuoto_koodi(jarjestamismuoto_koodi):
    validate_z2_koodi(jarjestamismuoto_koodi, Koodistot.jarjestamismuoto_koodit.value)


def validate_toimintamuoto_koodi(toimintamuoto_koodi):
    validate_z2_koodi(toimintamuoto_koodi, Koodistot.toimintamuoto_koodit.value)


def validate_kasvatusopillinen_jarjestelma_koodi(kasvatusopillinen_jarjestelma_koodi):
    validate_z2_koodi(kasvatusopillinen_jarjestelma_koodi, Koodistot.kasvatusopillinen_jarjestelma_koodit.value)


def validate_toimintapainotus_koodi(toimintapainotus_koodi):
    validate_z2_koodi(toimintapainotus_koodi, Koodistot.toiminnallinen_painotus_koodit.value)


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


def validate_tyosuhde_koodi(tyosuhde_koodi):
    validate_z2_koodi(tyosuhde_koodi, Koodistot.tyosuhde_koodit.value)


def validate_tyoaika_koodi(tyoaika_koodi):
    validate_z2_koodi(tyoaika_koodi, Koodistot.tyoaika_koodit.value)


def validate_tehtavanimike_koodi(tehtavanimike_koodi):
    validate_z2_koodi(tehtavanimike_koodi, Koodistot.tehtavanimike_koodit.value)


def validate_kieli_koodi(kieli_koodi):
    validate_z2_koodi(kieli_koodi, Koodistot.kieli_koodit.value)


def validate_sukupuoli_koodi(sukupuoli_koodi):
    validate_z2_koodi(sukupuoli_koodi, Koodistot.sukupuoli_koodit.value)


def validate_tutkinto_koodi(tutkinto_koodi):
    validate_z2_koodi(tutkinto_koodi, Koodistot.tutkinto_koodit.value)


def validate_lahdejarjestelma_koodi(lahdejarjestelma_koodi):
    validate_z2_koodi(lahdejarjestelma_koodi, Koodistot.lahdejarjestelma_koodit.value)


def validate_kieli_koodi_array(kieli_koodi):
    pass


def validate_IBAN_koodi(IBAN_koodi):
    try:
        IBAN = IBAN_koodi.replace(' ', '')
        if len(IBAN) != 18:
            raise ValidationErrorRest([ErrorMessages.VJ009.value])
        if IBAN[:2].lower() != 'fi':
            raise ValidationErrorRest([ErrorMessages.VJ009.value])
        IBA = IBAN[4:] + '1518' + IBAN[2:4]
        check = int(IBA) % 97
        if check != 1:
            raise ValidationErrorRest([ErrorMessages.VJ009.value])
    except (TypeError, ValueError, ValidationError):
        raise ValidationErrorRest([ErrorMessages.VJ009.value])


def validate_puhelinnumero(puhelinnumero):
    puhelinnumero = puhelinnumero.replace('-', '')
    puhelinnumero = puhelinnumero.replace(' ', '')
    if not puhelinnumero:
        raise ValidationErrorRest([ErrorMessages.GE001.value])
    puhelinnumero_regex = re.compile(r'^(\+358)[1-9][0-9]{5,10}')
    if not puhelinnumero_regex.fullmatch(puhelinnumero):
        raise ValidationErrorRest([ErrorMessages.MI006.value])


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
            raise ValidationErrorRest(msg)


def validate_dates_within_toimipaikka(validated_data, toimipaikka_obj):
    """
    Check validity of user-submitted toiminnallinenpainotus dates against toimipaikka dates.
    """
    if 'alkamis_pvm' in validated_data:
        if not validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], toimipaikka_obj.paattymis_pvm):
            raise ValidationErrorRest({'alkamis_pvm': [ErrorMessages.TP010.value]})
        if not validate_paivamaara1_after_paivamaara2(validated_data['alkamis_pvm'], toimipaikka_obj.alkamis_pvm, can_be_same=True):
            raise ValidationErrorRest({'alkamis_pvm': [ErrorMessages.TP011.value]})
    if 'paattymis_pvm' in validated_data:
        if not validate_paivamaara1_before_paivamaara2(validated_data['paattymis_pvm'], toimipaikka_obj.paattymis_pvm, can_be_same=True):
            raise ValidationErrorRest({'paattymis_pvm': [ErrorMessages.TP012.value]})


def validate_oid(oid, field_name):
    oid_sections = oid.split('.')
    if len(oid_sections) != 6:
        raise ValidationErrorRest({field_name: [ErrorMessages.MI007.value]})
    oph_part = '.'.join(oid_sections[:4])
    identifier = oid_sections[-1]
    if oph_part != '1.2.246.562':
        raise ValidationErrorRest({field_name: [ErrorMessages.MI008.value]})
    oidpattern = re.compile('^[1-9]{1}[0-9]{10,21}$')
    if not oidpattern.match(identifier):
        raise ValidationErrorRest({field_name: [ErrorMessages.MI009.value]})


def validate_organisaatio_oid(oid):
    field_name = 'organisaatio_oid'
    validate_oid(oid, field_name)
    oid_sections = oid.split('.')
    if oid_sections[4] != '10':
        raise ValidationErrorRest({field_name: [ErrorMessages.MI010.value]})


def validate_henkilo_oid(oid):
    field_name = 'henkilo_oid'
    validate_oid(oid, field_name)
    oid_sections = oid.split('.')
    if oid_sections[4] != '24':
        raise ValidationErrorRest({field_name: [ErrorMessages.MI011.value]})


def validate_nimi(nimi):
    if not bool(re.match("^[a-zà-öø-ÿåäöÅÄÖA-ZÀ-ÖØ-ß',-.`´ ]+$", nimi)):
        raise ValidationErrorRest([ErrorMessages.HE012.value])
    if nimi.startswith('-') or nimi.endswith('-') or '--' in nimi:
        raise ValidationErrorRest([ErrorMessages.HE013.value])


def validate_toimipaikan_nimi(toimipaikan_nimi):
    special_characters_partial = ['/', '&', '’', '\'', '`', '´', '+', '-', ',', '(']  # Allow toimipaikan nimi to end with '.' and ')'
    special_characters_full = special_characters_partial + ['.', ')']

    # Important to have dash "-" in the end of the regex below
    toimipaikan_nimi_clean = re.sub(r'[/&’\'`´+(),.-]', '', toimipaikan_nimi)
    if not toimipaikan_nimi_clean.replace(' ', '').isalnum():
        raise ValidationErrorRest({'nimi': [ErrorMessages.TP013.value]})

    # Checking for name length (min 2)
    if len(toimipaikan_nimi) < 2:
        raise ValidationErrorRest({'nimi': [ErrorMessages.TP014.value]})

    # Checking for consecutive repeating special characters (max 2)
    toimipaikan_nimi_simple = re.sub(r'[/&’\'`´+(),.-]', '0', toimipaikan_nimi)
    if '000' in toimipaikan_nimi_simple:
        raise ValidationErrorRest({'nimi': [ErrorMessages.TP015.value]})

    if (toimipaikan_nimi.startswith(tuple(special_characters_full)) or
            toimipaikan_nimi.endswith(tuple(special_characters_partial)) or
            '  ' in toimipaikan_nimi):
        raise ValidationErrorRest({'nimi': ErrorMessages.TP016.value})


def validate_tunniste(tunniste):
    # Validate that tunniste is not hetu
    is_hetu = True
    try:
        validate_henkilotunnus(tunniste)
    except ValidationErrorRest:
        is_hetu = False

    # Validate allowed characters
    pattern = re.compile(r'[a-zA-Z0-9.\-_]+')
    is_valid_characters = pattern.fullmatch(tunniste)

    if is_hetu or not is_valid_characters:
        raise ValidationErrorRest([ErrorMessages.MI012.value])


def validate_unique_lahdejarjestelma_tunniste_pair(self, model):
    """
    17.04.2020 UniqueConstraint with condition increments primary key on every validation check,
    so implement custom unique validation for lahdejarjestelma tunniste pair
    """

    # TODO: Remove this if else block when lahdejarjestelma is mandatory for vakatiedot
    if not self.lahdejarjestelma:
        if self.tunniste:
            raise ValidationErrorRest({'errors': [ErrorMessages.MI018.value]})
        else:
            # lahdejarjestelma and tunniste are empty
            return

    # Ignored if tunniste is not given
    if not self.tunniste:
        return

    if model.objects.filter(~Q(pk=self.pk) & Q(lahdejarjestelma=self.lahdejarjestelma) &
                            Q(tunniste=self.tunniste)).exists():
        raise ValidationErrorRest({'errors': [ErrorMessages.MI013.value]})


def validate_vaka_date(date):
    date_limit = datetime.date(2000, 1, 1)
    if not validate_paivamaara1_after_paivamaara2(date, date_limit, can_be_same=True):
        raise ValidationErrorRest([ErrorMessages.MI014.value])


def validate_taydennyskoulutus_suoritus_pvm(date):
    date_limit = datetime.date(2020, 9, 1)
    if not validate_paivamaara1_after_paivamaara2(date, date_limit, can_be_same=True):
        raise ValidationErrorRest([ErrorMessages.TK015.value])


def validate_palvelussuhde_paattymis_pvm(date):
    date_limit = datetime.date(2020, 9, 1)
    if not validate_paivamaara1_after_paivamaara2(date, date_limit, can_be_same=True):
        raise ValidationErrorRest([ErrorMessages.PS007.value])


def validate_pidempi_poissaolo_paattymis_pvm(date):
    date_limit = datetime.date(2020, 9, 1)
    if not validate_paivamaara1_after_paivamaara2(date, date_limit, can_be_same=True):
        raise ValidationErrorRest([ErrorMessages.PP008.value])


@deconstructible
class create_validate_decimal_steps:
    def __init__(self, stepsize):
        if not isinstance(stepsize, decimal.Decimal):
            stepsize = decimal.Decimal(stepsize)
        self.stepsize = stepsize

    def __call__(self, value):
        if value % self.stepsize != 0:
            raise ValidationErrorRest([ErrorMessages.GE018.value])

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
    excluded_fields = ['muutos_pvm', 'changed_by', ]
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
    ignore_fields_list = (('id', 'lahdejarjestelma', 'tunniste', 'luonti_pvm', 'muutos_pvm', 'changed_by',) +
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
        raise ValidationErrorRest({'errors': [error]})
