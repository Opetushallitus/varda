import datetime
import ipaddress
import re
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from rest_framework.exceptions import ValidationError as ValidationErrorRest

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
    if ("henkilotunnus" not in validated_data and "henkilo_oid" not in validated_data or
            "henkilotunnus" in validated_data and "henkilo_oid" in validated_data):
        error_msg = "Either henkilotunnus or henkilo_oid is needed. But not both."
        raise ValidationErrorRest({"non_field_errors": [error_msg, ]})


def validate_henkilotunnus(henkilotunnus):
    """
    Validate the date, the middle character, and the identification part.
    """
    if len(henkilotunnus) != 11:
        error_msg = henkilotunnus + " : Length incorrect."
        raise ValidationErrorRest({"henkilotunnus": [error_msg, ]})
    day = henkilotunnus[:2]
    month = henkilotunnus[2:4]
    year = henkilotunnus[4:6]
    century = henkilotunnus[6]

    check_tilapainen_hetu(henkilotunnus)
    if century not in ("-", "A"):
        error_msg = henkilotunnus + " : Century character incorrect."
        raise ValidationErrorRest({"henkilotunnus": [error_msg, ]})
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
        error_msg = henkilotunnus + " : Date incorrect."
        raise ValidationErrorRest({"henkilotunnus": [error_msg, ]})
    checknumber = henkilotunnus[:6] + henkilotunnus[7:10]
    check = henkilotunnus[10]
    code = '0123456789ABCDEFHJKLMNPRSTUVWXY'
    try:
        remainder = int(checknumber) % 31
        if check != code[remainder]:
            raise Exception()
    except Exception:
        error_msg = henkilotunnus + " : ID-number or control character incorrect."
        raise ValidationErrorRest({"henkilotunnus": [error_msg, ]})


def check_tilapainen_hetu(henkilotunnus):
    if settings.PRODUCTION_ENV:
        try:
            individual_number = int(henkilotunnus[7:10])
            if individual_number < 2 or individual_number > 899:
                raise Exception()
        except Exception:
            error_msg = henkilotunnus + " : Temporary personal identification is not permitted."
            raise ValidationErrorRest({"henkilotunnus": [error_msg, ]})


def validate_kutsumanimi(etunimet, kutsumanimi):
    """
    e.g. Liisa-Marja Tuuli -> valid kutsumanimet: ['liisa-marja', 'liisa', 'marja', 'tuuli']

    First, check that kutsumanimi is one name.
    """
    splitted_kutsumanimi_array = kutsumanimi.split(" ")
    kutsumanimi_array = list(filter(None, splitted_kutsumanimi_array))  # Remove empty, i.e. ''
    if len(kutsumanimi_array) != 1:
        error_msg = "Kutsumanimi must be one name."
        raise ValidationErrorRest({"kutsumanimi": [error_msg, ]})
    validated_kutsumanimi = kutsumanimi_array[0].lower()

    splitted_etunimet_array = etunimet.split(" ")
    etunimet_array = list(filter(None, splitted_etunimet_array))
    etunimet_array_final = etunimet_array

    for etunimi in etunimet_array:
        etunimet_splitted_by_dash_array = etunimi.split("-")
        if len(etunimet_splitted_by_dash_array) > 1:  # Do nothing if name doesn't have "-" in it (to avoid duplicates)
            for nimi in etunimet_splitted_by_dash_array:
                etunimet_array_final.append(nimi)

    for etunimi in etunimet_array_final:
        if etunimi.lower() == validated_kutsumanimi:
            return

    error_msg = "Kutsumanimi is not valid."
    raise ValidationErrorRest({"kutsumanimi": [error_msg, ]})


def validate_postinumero(postinumero):
    """
    Validate the postal code: numeric, length 5 string
    """
    if (len(postinumero) == 5) and postinumero.isnumeric() and postinumero != '00000':
        pass
    else:
        error_msg = postinumero + " : Postinumero is incorrect."
        raise ValidationError(error_msg)


def validate_y_tunnus(y_tunnus):
    """
    Validation of y-tunnus: http://tarkistusmerkit.teppovuori.fi/
    """
    if len(y_tunnus) != 9:
        error_msg = y_tunnus + " : Y-tunnus length is incorrect."
        raise ValidationError(error_msg)
    tunnus = y_tunnus[:7]
    hyphen = y_tunnus[7]
    if hyphen != '-':
        error_msg = y_tunnus + " : Y-tunnus has no hyphen."
        raise ValidationError(error_msg)
    check = y_tunnus[8]
    multiplier = [7, 9, 10, 5, 8, 4, 2]
    try:
        summa = sum([int(tunnus[i]) * multiplier[i] for i in range(len(tunnus))])
        remainder = summa % 11
        if remainder == 0:
            checknumber = 0
        elif remainder == 1:
            error_msg = y_tunnus + " : Y-tunnus check number cannot be 1."
            raise ValidationError(error_msg)
        else:
            checknumber = 11 - remainder
        if checknumber != int(check):
            error_msg = y_tunnus + " : Y-tunnus has incorrect check number."
            raise ValidationError(error_msg)
    except Exception:
        error_msg = y_tunnus + " : Y-tunnus has incorrect check number."
        raise ValidationError(error_msg)


def validate_arrayfield(provided_array):
    if not len(provided_array):
        raise ValidationError('You must give at least one value.')


def validate_ipv4_address(ip_address):
    if ip_address:
        try:
            ipaddress.ip_network(ip_address)
        except ValueError:
            err_msg = ip_address + " : Not a valid IPv4-address."
            raise ValidationError(err_msg)


def validate_ipv6_address(ip_address):
    if ip_address:
        try:
            ipaddress.ip_network(ip_address)
        except ValueError:
            err_msg = ip_address + " : Not a valid IPv6-address."
            raise ValidationError(err_msg)


def get_koodisto():
    from varda.models import Z2_Koodisto  # if import is on top of the file, it causes ImportError (probably due to circular references)
    if Z2_Koodisto.objects.filter(pk=1).exists():
        koodisto = Z2_Koodisto.objects.filter(pk=1)
        return koodisto[0]
    else:
        raise ValidationError('Validation cannot be done right now. No access to codes (koodistot).')


def validate_koodi_in_general(koodi):
    splitted_koodi = koodi.split(" ")
    if len(splitted_koodi) > 1:
        raise ValidationError('Koodi has spaces. Not allowed.')
    if not koodi.isalnum():
        raise ValidationError('Koodi has special characters. Not allowed.')


def validate_z2_koodi(koodi, field_name, code_name):
    validate_koodi_in_general(koodi)
    koodisto = get_koodisto()
    if getattr(koodisto, field_name):
        koodit = [z2_koodi.lower() for z2_koodi in getattr(koodisto, field_name)]
    else:
        raise ValidationError('Problem with ' + field_name + '-codes.')
    if koodi.lower() not in koodit:
        error_msg = koodi + ' : Not a valid ' + code_name + '.'
        raise ValidationError(error_msg)


def validate_maksun_peruste_koodi(maksun_peruste_koodi):
    validate_z2_koodi(maksun_peruste_koodi, 'maksun_peruste_koodit', 'maksun_peruste_koodi')


def validate_kunta_koodi(kunta_koodi):
    validate_z2_koodi(kunta_koodi, 'kunta_koodit', 'kunta_koodi')


def validate_jarjestamismuoto_koodi(jarjestamismuoto_koodi):
    validate_z2_koodi(jarjestamismuoto_koodi, 'jarjestamismuoto_koodit', 'jarjestamismuoto_koodi')


def validate_toimintamuoto_koodi(toimintamuoto_koodi):
    validate_z2_koodi(toimintamuoto_koodi, 'toimintamuoto_koodit', 'toimintamuoto_koodi')


def validate_kasvatusopillinen_jarjestelma_koodi(kasvatusopillinen_jarjestelma_koodi):
    validate_z2_koodi(kasvatusopillinen_jarjestelma_koodi,
                      'kasvatusopillinen_jarjestelma_koodit',
                      'kasvatusopillinen_jarjestelma_koodi')


def validate_toimintapainotus_koodi(toimintapainotus_koodi):
    validate_z2_koodi(toimintapainotus_koodi, 'toiminnallinen_painotus_koodit', 'toimintapainotus_koodi')


def validate_tutkintonimike_koodi(tutkintonimike_koodi):
    validate_z2_koodi(tutkintonimike_koodi, 'tutkintonimike_koodit', 'tutkintonimike_koodi')


def validate_tyosuhde_koodi(tyosuhde_koodi):
    validate_z2_koodi(tyosuhde_koodi, 'tyosuhde_koodit', 'tyosuhde_koodi')


def validate_tyoaika_koodi(tyoaika_koodi):
    validate_z2_koodi(tyoaika_koodi, 'tyoaika_koodit', 'tyoaika_koodi')


def validate_tyotehtava_koodi(tyotehtava_koodi):
    validate_z2_koodi(tyotehtava_koodi, 'tyotehtava_koodit', 'tyotehtava_koodi')


def validate_kieli_koodi(kieli_koodi):
    validate_z2_koodi(kieli_koodi, 'kieli_koodit', 'kieli_koodi')


def validate_sukupuoli_koodi(sukupuoli_koodi):
    validate_z2_koodi(sukupuoli_koodi, 'sukupuoli_koodit', 'sukupuoli_koodi')


def validate_opiskeluoikeudentila_koodi(opiskeluoikeudentila_koodi):
    validate_z2_koodi(opiskeluoikeudentila_koodi, 'opiskeluoikeuden_tila_koodit', 'opiskeluoikeudentila_koodi')


def validate_tutkinto_koodi(tutkinto_koodi):
    validate_z2_koodi(tutkinto_koodi, 'tutkinto_koodit', 'tutkinto_koodi')


def validate_lahdejarjestelma_koodi(lahdejarjestelma_koodi):
    validate_z2_koodi(lahdejarjestelma_koodi, 'lahdejarjestelma_koodit', 'lahdejarjestelma_koodi')


def validate_kieli_koodi_array(kieli_koodi):
    pass


def validate_IBAN_koodi(IBAN_koodi):
    try:
        IBAN = IBAN_koodi.replace(' ', '')
        if len(IBAN) != 18:
            raise ValidationError()
        if IBAN[:2].lower() != "fi":
            raise ValidationError()
        IBA = IBAN[4:] + "1518" + IBAN[2:4]
        check = int(IBA) % 97
        if check != 1:
            raise ValidationError()
    except (TypeError, ValueError, ValidationError):
        error_msg = IBAN_koodi + " : Not a valid IBAN code."
        raise ValidationError(error_msg)


def validate_puhelinnumero(puhelinnumero):
    puhelinnumero = puhelinnumero.replace('-', '')
    puhelinnumero = puhelinnumero.replace(' ', '')
    if not puhelinnumero:
        raise ValidationError('puhelinnumero must be given.')
    puhelinnumero_regex = re.compile(r'^(\+358)[1-9][0-9]{5,10}')
    if not puhelinnumero_regex.match(puhelinnumero):
        error_msg = puhelinnumero + " : Not a valid Finnish phone number."
        raise ValidationError(error_msg)


def validate_paivamaara1_before_paivamaara2(paivamaara1, paivamaara2, can_be_same=False):
    if not isinstance(paivamaara1, datetime.date):
        if isinstance(paivamaara1, str):
            paivamaara1 = datetime.datetime.strptime(paivamaara1.replace("-", ""), "%Y%m%d").date()
        else:
            paivamaara1 = datetime.date(2000, 1, 1)
    if not isinstance(paivamaara2, datetime.date):
        if isinstance(paivamaara2, str):
            paivamaara2 = datetime.datetime.strptime(paivamaara2.replace("-", ""), "%Y%m%d").date()
        else:
            paivamaara2 = datetime.date(2100, 1, 1)
    if paivamaara1 > paivamaara2 or (paivamaara1 == paivamaara2 and not can_be_same):
        return False
    else:
        return True


def validate_paivamaara1_after_paivamaara2(paivamaara1, paivamaara2, can_be_same=False):
    return not validate_paivamaara1_before_paivamaara2(paivamaara1, paivamaara2, not can_be_same)


def validate_oid(oid):
    oid_sections = oid.split('.')
    if len(oid_sections) != 6:
        error_msg = "Number of sections in OID is incorrect."
        raise ValidationErrorRest({"oid": [error_msg, ]})
    oph_part = ".".join(oid_sections[:4])
    identifier = oid_sections[-1]
    if oph_part != "1.2.246.562":
        error_msg = "OPH part of OID is incorrect."
        raise ValidationErrorRest({"oid": [error_msg, ]})
    oidpattern = re.compile('^[1-9]{1}[0-9]{10,21}$')
    if not oidpattern.match(identifier):
        error_msg = "OID identifier is incorrect."
        raise ValidationErrorRest({"oid": [error_msg, ]})


def validate_organisaatio_oid(oid):
    validate_oid(oid)
    oid_sections = oid.split('.')
    if oid_sections[4] != "10":
        error_msg = "Not an OID for an organization."
        raise ValidationErrorRest({"oid": [error_msg, ]})


def validate_henkilo_oid(oid):
    validate_oid(oid)
    oid_sections = oid.split('.')
    if oid_sections[4] != "24":
        error_msg = "Not an OID for a person."
        raise ValidationErrorRest({"oid": [error_msg, ]})


def validate_nimi(nimi):
    if not bool(re.match("^[a-zà-öø-ÿåäöÅÄÖA-ZÀ-ÖØ-ß',-.`´ ]+$", nimi)):
        raise ValidationErrorRest("Name has disallowed characters.")
    if nimi.startswith("-") or nimi.endswith("-") or "--" in nimi:
        raise ValidationErrorRest("Incorrect format.")


def validate_toimipaikan_nimi(toimipaikan_nimi):
    special_characters_partial = ["/", "&", "’", "'", "`", "´", "+", "-", ",", "("]  # Allow toimipaikan nimi to end with '.' and ')'
    special_characters_full = special_characters_partial + [".", ")"]

    # Important to have dash "-" in the end of the regex below
    toimipaikan_nimi_clean = re.sub(r'[/&’\'`´+(),.-]', '', toimipaikan_nimi)
    if not toimipaikan_nimi_clean.replace(" ", "").isalnum():
        raise ValidationErrorRest({"toimipaikka": "Toimipaikan nimi has disallowed characters."})

    # Checking for name length (min 2)
    if len(toimipaikan_nimi) < 2:
        raise ValidationErrorRest({"toimipaikka": "Name must have at least 2 characters."})

    # Checking for consecutive repeating special characters (max 2)
    toimipaikan_nimi_simple = re.sub(r'[/&’\'`´+(),.-]', '0', toimipaikan_nimi)
    if "000" in toimipaikan_nimi_simple:
        raise ValidationErrorRest({"toimipaikka": "Maximum 2 consecutively repeating special characters are allowed."})

    if (toimipaikan_nimi.startswith(tuple(special_characters_full)) or
            toimipaikan_nimi.endswith(tuple(special_characters_partial)) or
            "  " in toimipaikan_nimi):
        raise ValidationErrorRest({"toimipaikka": "Incorrect format."})


def validate_tunniste(tunniste):
    # Validate that tunniste is not hetu
    is_hetu = True
    try:
        validate_henkilotunnus(tunniste)
    except ValidationErrorRest:
        is_hetu = False

    if is_hetu:
        error_msg = tunniste + ' : Not a valid tunniste.'
        raise ValidationError(error_msg)


def validate_unique_lahdejarjestelma_tunniste_pair(self, model):
    """
    17.04.2020 UniqueConstraint with condition increments primary key on every validation check,
    so implement custom unique validation for lahdejarjestelma tunniste pair
    """

    # Ignored if tunniste is not given
    if not self.tunniste:
        return

    if model.objects.filter(~Q(pk=self.pk) & Q(lahdejarjestelma=self.lahdejarjestelma) &
                            Q(tunniste=self.tunniste)).exists():
        raise ValidationError({'non_field_errors': ['lahdejarjestelma and tunniste pair already exists.']})
