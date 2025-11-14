import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from varda.constants import YRITYSMUOTO_KUNTA
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.enums.data_category import DataCategory
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.enums.koodistot import Koodistot
from varda.enums.message_type import MessageType
from varda.enums.supported_language import SupportedLanguage
from varda.enums.translation import Translation
from varda.kayttooikeuspalvelu import get_paakayttaja_users_with_yhteystieto_data
from varda.lokalisointipalvelu import get_translation
from varda.misc import TemporaryObject
from varda.misc_queries import get_active_vakajarjestajat
from varda.models import Aikaleima, Organisaatio, Z11_MessageLog, Z11_MessageTarget, Z6_LastRequest
from varda.viewsets_reporting import ErrorReportLapsetViewSet, ErrorReportTyontekijatViewSet, ErrorReportToimipaikatViewSet


logger = logging.getLogger(__name__)


def update_message_targets_and_paakayttaja_status():
    # Delete old targets
    Z11_MessageTarget.objects.all().delete()

    paakayttaja_list = get_paakayttaja_users_with_yhteystieto_data()
    if paakayttaja_list is None:
        # Error getting VARDA-PAAKAYTTAJA users
        return None

    organisaatio_id_set_with_paakayttaja = set()
    for paakayttaja_data in paakayttaja_list:
        for organisaatio_id in paakayttaja_data["organisaatio_id_set"]:
            organisaatio_id_set_with_paakayttaja.add(organisaatio_id)
            # Organisaatio has VARDA-PAAKAYTTAJA user, delete related Aikaleima
            (Aikaleima.objects.filter(avain=AikaleimaAvain.NO_PAAKAYTTAJA.value, organisaatio_id=organisaatio_id).delete())

            yhteystieto_data = paakayttaja_data["yhteystieto_data"]
            if email := yhteystieto_data["email"]:
                default_values = {}
                if language := yhteystieto_data["language"]:
                    # language may be None, use field default value in such case
                    default_values["language"] = language

                # Use get_or_create, in case users use shared email addresses
                Z11_MessageTarget.objects.get_or_create(
                    organisaatio_id=organisaatio_id,
                    user_type=Kayttajatyyppi.PAAKAYTTAJA.value,
                    email=email,
                    defaults=default_values,
                )

    # Update Aikaleima for Organisaatio objects that do not have VARDA-PAAKAYTTAJA user
    for organisaatio in Organisaatio.vakajarjestajat.exclude(id__in=organisaatio_id_set_with_paakayttaja):
        # Create Aikaleima if it does not exist yet
        Aikaleima.objects.get_or_create(
            avain=AikaleimaAvain.NO_PAAKAYTTAJA.value, organisaatio_id=organisaatio.id, defaults={"aikaleima": timezone.now()}
        )


def send_no_paakayttaja_message():
    message_type = MessageType.NO_PAAKAYTTAJA.value

    now = timezone.now()
    error_limit = now - timedelta(days=30)
    frequency_limit = now - timedelta(days=30)

    active_organisaatio_id_list = get_active_vakajarjestajat().values_list("id", flat=True)

    # Send email if Organisaatio has not had VARDA-PAAKAYTTAJA since error_limit
    aikaleima_qs = Aikaleima.objects.filter(avain=AikaleimaAvain.NO_PAAKAYTTAJA.value, aikaleima__lt=error_limit)
    for aikaleima in aikaleima_qs:
        organisaatio = aikaleima.organisaatio
        last_message_qs = Z11_MessageLog.objects.filter(
            message_type=message_type, organisaatio=organisaatio, timestamp__gt=frequency_limit
        )
        if organisaatio.id in active_organisaatio_id_list and not last_message_qs.exists():
            # Send email if one has not been sent after frequency_limit and if Organisaatio is currently active
            if email := organisaatio.sahkopostiosoite:
                _send_message(
                    message_type,
                    organisaatio,
                    email,
                    organisaatio.ytjkieli,
                    Translation.EMAIL_NO_PAAKAYTTAJA_SUBJECT.value,
                    Translation.EMAIL_NO_PAAKAYTTAJA_MESSAGE.value,
                    [organisaatio.nimi],
                )
            else:
                # Organisaatio does not have email address
                _send_undelivered_message_to_oph(message_type, organisaatio)


def send_puutteelliset_tiedot_message():
    message_type = MessageType.PUUTTEELLISET_TIEDOT.value

    organisaatio_qs = get_active_vakajarjestajat()
    for organisaatio in organisaatio_qs:
        vaka_errors = {}
        henkilosto_errors = {}
        toimipaikka_errors = {}

        for viewset, error_dict in [
            (
                ErrorReportLapsetViewSet(),
                vaka_errors,
            ),
            (
                ErrorReportTyontekijatViewSet(),
                henkilosto_errors,
            ),
            (
                ErrorReportToimipaikatViewSet(),
                toimipaikka_errors,
            ),
        ]:
            # Initialize ViewSet by setting properties
            viewset.vakajarjestaja_id = organisaatio.id
            viewset.vakajarjestaja_oid = organisaatio.organisaatio_oid
            viewset.is_vakatiedot_permissions = True
            viewset.is_huoltajatiedot_permissions = True
            viewset.is_tyontekijatiedot_permissions = True
            viewset.format_kwarg = None
            temp_request_object = TemporaryObject()
            temp_request_object.query_params = {}
            viewset.request = temp_request_object

            queryset = viewset.get_queryset()
            serializer_data = viewset.get_serializer(queryset, many=True).data

            for object_instance in serializer_data:
                for error in object_instance["errors"]:
                    error_code = error["error_code"]
                    error_dict[error_code] = error_dict.get(error_code, 0) + len(error["model_id_list"])

        if vaka_errors or henkilosto_errors or toimipaikka_errors:
            message_target_qs = Z11_MessageTarget.objects.filter(organisaatio=organisaatio)
            if message_target_qs.exists():
                error_string_dict = _parse_puutteelliset_tiedot_message(vaka_errors, henkilosto_errors, toimipaikka_errors)
                for message_target in message_target_qs:
                    error_string = error_string_dict.get(
                        message_target.language.upper(), error_string_dict[SupportedLanguage.FI.value]
                    )
                    _send_message(
                        message_type,
                        organisaatio,
                        message_target.email,
                        message_target.language,
                        Translation.EMAIL_PUUTTEELLISET_SUBJECT.value,
                        Translation.EMAIL_PUUTTEELLISET_MESSAGE.value,
                        [organisaatio.nimi, error_string],
                    )
            else:
                # Organisaatio does not have message targets (VARDA-PAAKAYTTAJA users)
                _send_undelivered_message_to_oph(message_type, organisaatio)


def _parse_puutteelliset_tiedot_message(vaka_errors, henkilosto_errors, toimipaikka_errors):
    # Parse errors to readable format
    error_string_dict = {}
    error_category_tuple = (
        (
            vaka_errors,
            Translation.EMAIL_PUUTTEELLISET_MESSAGE_VARHAISKASVATUS.value,
        ),
        (
            henkilosto_errors,
            Translation.EMAIL_PUUTTEELLISET_MESSAGE_HENKILOSTO.value,
        ),
        (
            toimipaikka_errors,
            Translation.EMAIL_PUUTTEELLISET_MESSAGE_TOIMIPAIKKA.value,
        ),
    )
    for error_dict, category_title in error_category_tuple:
        if not error_dict:
            # Skip empty error category
            continue
        for language in SupportedLanguage.list():
            # Build error code string for each supported language
            error_string_dict[language] = (
                error_string_dict.get(language, "") + f"\n\n{get_translation(category_title, locale=language)}\n"
            )
            for error_key, error_value in error_dict.items():
                error_translation = get_translation(error_key, locale=language, category=Koodistot.virhe_koodit.value)
                error_template = get_translation(Translation.EMAIL_PUUTTEELLISET_MESSAGE_ERROR_TEMPLATE.value, locale=language)
                error_string_dict[language] += f"{error_template.format(error_translation, error_key, error_value)}\n"
            # Remove newlines from start and end of the string
            error_string_dict[language] = error_string_dict[language].strip()
    return error_string_dict


def send_no_transfers_message():
    message_type = MessageType.NO_TRANSFERS.value

    now = timezone.now()
    error_limit_kunta = now - timedelta(days=30)
    frequency_limit_kunta = now - timedelta(days=30)
    error_limit_yksityinen = now - timedelta(days=180)
    frequency_limit_yksityinen = now - timedelta(days=180)

    organisaatio_qs = get_active_vakajarjestajat()
    for organisaatio in organisaatio_qs:
        # Different limits and messages for kunnallinen and yksityinen Organisaatio
        if organisaatio.yritysmuoto in YRITYSMUOTO_KUNTA:
            error_limit = error_limit_kunta
            frequency_limit = frequency_limit_kunta
            message_key = Translation.EMAIL_NO_TRANSFERS_MESSAGE_KUNTA.value
        else:
            error_limit = error_limit_yksityinen
            frequency_limit = frequency_limit_yksityinen
            message_key = Translation.EMAIL_NO_TRANSFERS_MESSAGE_YKSITYINEN.value

        datetime_format = "%d.%m.%Y %H.%M.%S"
        last_request_vaka = (
            Z6_LastRequest.objects.filter(
                vakajarjestaja=organisaatio, data_category=DataCategory.VARHAISKASVATUS.value, last_successful__isnull=False
            )
            .order_by("-last_successful")
            .first()
        )
        # Defaults to error_limit so that message is sent also if no transfers have been made
        last_successful_vaka = getattr(last_request_vaka, "last_successful", error_limit)
        last_request_henkilosto = (
            Z6_LastRequest.objects.filter(
                vakajarjestaja=organisaatio, data_category=DataCategory.HENKILOSTO.value, last_successful__isnull=False
            )
            .order_by("-last_successful")
            .first()
        )
        last_successful_henkilosto = getattr(last_request_henkilosto, "last_successful", error_limit)

        last_message_qs = Z11_MessageLog.objects.filter(
            message_type=message_type, organisaatio=organisaatio, timestamp__gt=frequency_limit
        )

        if (
            (last_successful_vaka <= error_limit or last_successful_henkilosto <= error_limit)
            and organisaatio.luonti_pvm < error_limit
            and not last_message_qs.exists()
        ):
            # Send email if last_successful_vaka or last_successful_henkilosto transfer timestamps are older
            # than error_limit, and Organisaatio has been created before error_limit and if email has not been
            # sent after frequency_limit
            message_target_qs = Z11_MessageTarget.objects.filter(organisaatio=organisaatio)
            if message_target_qs.exists():
                for message_target in message_target_qs:
                    _send_message(
                        message_type,
                        organisaatio,
                        message_target.email,
                        message_target.language,
                        Translation.EMAIL_NO_TRANSFERS_SUBJECT.value,
                        message_key,
                        [
                            organisaatio.nimi,
                            last_successful_vaka.strftime(datetime_format),
                            last_successful_henkilosto.strftime(datetime_format),
                        ],
                    )
            else:
                # Organisaatio does not have message targets (VARDA-PAAKAYTTAJA users)
                _send_undelivered_message_to_oph(message_type, organisaatio)


def _send_message(message_type, organisaatio, email, language, subject_key, message_key, message_argument_list):
    logger.info(f"Sending {message_type} to {email}")
    message = get_translation(message_key, locale=language).format(*message_argument_list)
    send_mail(
        subject=get_translation(subject_key, locale=language),
        message=message,
        html_message=_get_html_message(message),
        # Pass None to from_email so settings.DEFAULT_FROM_EMAIL is used
        from_email=None,
        recipient_list=[email],
    )
    Z11_MessageLog.objects.create(message_type=message_type, organisaatio=organisaatio, email=email, timestamp=timezone.now())


def _send_undelivered_message_to_oph(message_type, organisaatio):
    email = settings.OPH_EMAIL
    logger.info(f"Could not deliver {message_type} for Organisaatio with ID {organisaatio.id}, sending notification to {email}")
    message = get_translation(Translation.EMAIL_COULD_NOT_DELIVER_MESSAGE.value).format(
        message_type, organisaatio.nimi, organisaatio.id
    )
    send_mail(
        subject=get_translation(Translation.EMAIL_COULD_NOT_DELIVER_SUBJECT.value),
        message=message,
        html_message=_get_html_message(message),
        # Pass None to from_email so settings.DEFAULT_FROM_EMAIL is used
        from_email=None,
        recipient_list=[email],
    )
    Z11_MessageLog.objects.create(message_type=message_type, organisaatio=organisaatio, email=email, timestamp=timezone.now())


def _get_html_message(message):
    """
    Different email programs handle line breaks differently, so convert message to HTML so that layout consistent.
    :param message: raw message with line breaks as \n
    :return: HTML style message
    """
    return message.replace("\n", "<br>")
