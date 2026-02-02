import logging
import uuid

from datetime import datetime, time

from django.http import Http404, HttpResponse
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import GenericViewSet

from varda.cache import get_paattymis_pvm_cache, set_paattymis_pvm_cache
from varda.constants import YRITYSMUOTO_KUNTA
from varda.enums.error_messages import ErrorMessages
from varda.enums.message_type import MessageType
from varda.enums.reporting import ReportStatus
from varda.misc import create_muistutus_report_csv
from varda.models import Henkilo, Z11_MessageLog
from varda.permissions import AdminOrOPHUser
from varda.request_logging import auditlogclass, request_log_viewset_decorator_factory
from varda.serializers_admin import AnonymisointiYhteenvetoSerializer, SetPaattymisPvmPostSerializer, SetPaattymisPvmGetSerializer
from varda.tasks import set_paattymis_pvm_for_vakajarjestaja_data_task
from varda.validators import validate_datetime_string


logger = logging.getLogger(__name__)


class AnonymisointiYhteenvetoViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda anonymisointi-yhteenveto.
    """

    queryset = Henkilo.objects.none()
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AnonymisointiYhteenvetoSerializer
    pagination_class = None

    def validate_henkilo_query_params(self, attribute):
        henkilo_id = self.request.query_params.get(attribute, None)
        if henkilo_id is not None:
            if henkilo_id.isdigit():
                try:
                    Henkilo.objects.get(id=int(henkilo_id))
                except Henkilo.DoesNotExist:
                    raise ValidationError({attribute: [ErrorMessages.MI015.value]})
            else:
                raise ValidationError({attribute: [ErrorMessages.MI015.value]})

    def _get_query_param(self, param_name):
        """
        :param param_name: query_param_name
        :return: parameter value as integer or None
        """
        query_param = self.request.query_params.get(param_name, None)
        if query_param and query_param.isdigit():
            return int(query_param)

    def validate_henkilo_ids_general(self):
        first_henkilo_id = self._get_query_param("first_henkilo_id")
        middle_henkilo_id = self._get_query_param("middle_henkilo_id")
        last_henkilo_id = self._get_query_param("last_henkilo_id")

        if first_henkilo_id and middle_henkilo_id and first_henkilo_id >= middle_henkilo_id:
            raise ValidationError({"first_henkilo_id": [ErrorMessages.MI017.value]})

        if first_henkilo_id and last_henkilo_id and first_henkilo_id >= last_henkilo_id:
            raise ValidationError({"first_henkilo_id": [ErrorMessages.MI017.value]})

        if middle_henkilo_id and last_henkilo_id and middle_henkilo_id >= last_henkilo_id:
            raise ValidationError({"middle_henkilo_id": [ErrorMessages.MI017.value]})

    def validate_query_params(self):
        self.validate_henkilo_query_params("first_henkilo_id")
        self.validate_henkilo_query_params("middle_henkilo_id")
        self.validate_henkilo_query_params("last_henkilo_id")
        self.validate_henkilo_ids_general()

    @swagger_auto_schema(responses={status.HTTP_200_OK: AnonymisointiYhteenvetoSerializer(many=False)})
    def list(self, request, *args, **kwargs):
        self.validate_query_params()
        serializer = self.get_serializer(request)
        return Response(serializer.data)


@auditlogclass
@request_log_viewset_decorator_factory()
class SetPaattymisPvmViewSet(GenericViewSet, RetrieveModelMixin, CreateModelMixin):
    permission_classes = (AdminOrOPHUser,)

    def get_queryset(self):
        return None

    def get_serializer_class(self):
        request = self.request
        if request.method == "POST":
            return SetPaattymisPvmPostSerializer
        return SetPaattymisPvmGetSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        vakajarjestaja = data["vakajarjestaja"]
        paattymis_pvm = data["paattymis_pvm"]

        identifier = uuid.uuid4()
        set_paattymis_pvm_cache(identifier, {"status": ReportStatus.CREATING.value})
        paattymis_pvm_str = paattymis_pvm.strftime("%Y-%m-%d")
        set_paattymis_pvm_for_vakajarjestaja_data_task.delay(vakajarjestaja.id, paattymis_pvm_str, identifier)

        headers = self.get_success_headers(serializer.data)
        result = {"identifier": identifier}
        return Response(self.get_serializer(result).data, status=status.HTTP_200_OK, headers=headers)

    def retrieve(self, request, *args, **kwargs):
        identifier = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field, None)
        if not identifier:
            raise Http404

        result = get_paattymis_pvm_cache(identifier)
        if not result:
            # Cache entry does not exist, task is not running or cache has been cleared
            raise ValidationError({"errors": [ErrorMessages.AD006.value]})

        return Response(self.get_serializer(result).data)


class MuistutusReportViewSet(GenericViewSet):
    permission_classes = (AdminOrOPHUser,)

    @action(url_path=r"alkupvm=(?P<alkupvm>[0-9-]+)/loppupvm=(?P<loppupvm>[0-9-]+)", detail=False)
    def get_messagelog_report_csv_by_dates(self, request, alkupvm, loppupvm):
        # validate dates
        alkupvm_datetime = validate_datetime_string(alkupvm, "alkupvm")
        loppupvm_datetime = validate_datetime_string(loppupvm, "loppupvm")

        # fix loppupvm time part 00:00:00 to 23:59:59
        loppupvm_datetime = datetime.combine(loppupvm_datetime.date(), time.max)

        msg_logs = (
            Z11_MessageLog.objects.filter(
                timestamp__gte=timezone.make_aware(alkupvm_datetime),
                timestamp__lte=timezone.make_aware(loppupvm_datetime),
                message_type=MessageType.NO_TRANSFERS.value,
                organisaatio__yritysmuoto__in=YRITYSMUOTO_KUNTA,
            )
            .select_related("organisaatio")
            .order_by("organisaatio__nimi")
            .distinct("organisaatio__nimi")
        )

        if not msg_logs.exists():
            return Response(status=status.HTTP_204_NO_CONTENT)

        csv_file = create_muistutus_report_csv(msg_logs)

        return HttpResponse(
            csv_file, content_type="text/csv", headers={"Content-Disposition": 'attachment; filename="output.csv"'}
        )  # HTTP_200_OK
