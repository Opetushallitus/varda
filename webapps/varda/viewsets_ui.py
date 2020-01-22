from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models import Q, F
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.filters import SearchFilter
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response

from varda.cache import create_cache_key, get_object_ids_user_has_permissions
from varda.cas.varda_permissions import IsVardaPaakayttaja
from varda import filters
from varda.misc_queries import get_paos_toimipaikat
from varda.models import Toimipaikka, VakaJarjestaja, Henkilo, Varhaiskasvatussuhde
from varda.permissions import CustomObjectPermissions, save_audit_log
from varda.serializers import PaosToimipaikkaSerializer, PaosVakaJarjestajaSerializer
from varda.serializers_ui import VakaJarjestajaUiSerializer, ToimipaikkaUiSerializer, ToimipaikanLapsetUISerializer


class UiVakajarjestajatViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda vakajarjestajien nimet
    """
    serializer_class = VakaJarjestajaUiSerializer
    queryset = VakaJarjestaja.objects.none()

    def list(self, request, *args, **kwargs):
        user = request.user
        if user.is_superuser:
            queryset = VakaJarjestaja.objects.all().order_by('nimi')
        else:
            model_name = 'vakajarjestaja'
            content_type = ContentType.objects.get(model=model_name)
            vakajarjestaja_ids = get_object_ids_user_has_permissions(user, model_name, content_type)
            queryset = VakaJarjestaja.objects.filter(id__in=vakajarjestaja_ids).order_by('nimi')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class NestedToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn vaka-järjestäjän kaikki toimipaikat. (dropdownia -varten)
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = None
    queryset = Toimipaikka.objects.none()
    serializer_class = ToimipaikkaUiSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
            'vakajarjestaja_pk': self.kwargs['vakajarjestaja_pk']
        }

    def get_vakajarjestaja(self, request, vakajarjestaja_pk=None):
        vakajarjestaja = get_object_or_404(VakaJarjestaja.objects.all(), pk=vakajarjestaja_pk)
        user = request.user
        if user.has_perm("view_vakajarjestaja", vakajarjestaja):
            return vakajarjestaja
        else:
            raise Http404("Not found.")

    def list(self, request, *args, **kwargs):
        if not kwargs['vakajarjestaja_pk'].isdigit():
            raise Http404("Not found.")

        vakajarjestaja_obj = self.get_vakajarjestaja(request, vakajarjestaja_pk=kwargs['vakajarjestaja_pk'])
        paos_toimipaikat = get_paos_toimipaikat(vakajarjestaja_obj)
        qs_own_toimipaikat = Q(vakajarjestaja=kwargs['vakajarjestaja_pk'])
        qs_paos_toimipaikat = Q(id__in=paos_toimipaikat)
        qs_all_toimipaikat = (Toimipaikka
                              .objects
                              .filter(qs_own_toimipaikat | qs_paos_toimipaikat)
                              .values('id', 'nimi', 'lahdejarjestelma', 'vakajarjestaja__id', 'vakajarjestaja__nimi')
                              .order_by('nimi'))

        save_audit_log(request.user, request.get_full_path())

        serializer = self.get_serializer(qs_all_toimipaikat, many=True)
        return Response(serializer.data)


class NestedAllToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    Rajapinta varda pääkäyttäjille paos-toimipaikkojen hakuun (jm02 ja jm03).
    """
    queryset = Toimipaikka.objects.all()
    permission_classes = (IsVardaPaakayttaja, )
    serializer_class = PaosToimipaikkaSerializer
    filter_backends = (SearchFilter, )
    search_fields = ['nimi', 'nimi_sv']

    def list(self, request, *args, **kwargs):
        vakajarjestaja_id = self.kwargs.get('vakajarjestaja_pk', None)
        if not vakajarjestaja_id or not vakajarjestaja_id.isdigit() or not get_object_or_404(VakaJarjestaja, pk=vakajarjestaja_id):
            raise Http404("Not found.")
        return super(NestedAllToimipaikkaViewSet, self).list(request, *args, **kwargs)

    def get_queryset(self, **kwargs):
        vakajarjestaja_id = self.kwargs.get('vakajarjestaja_pk', None)
        if not vakajarjestaja_id or not vakajarjestaja_id.isdigit():
            vakajarjestaja_id = None
        # Return only paos toimipaikat
        return Toimipaikka.objects.filter(vakajarjestaja__pk=vakajarjestaja_id,
                                          jarjestamismuoto_koodi__overlap=['jm02', 'jm03']).order_by('id')


class AllVakajarjestajaViewSet(GenericViewSet, ListModelMixin):
    """
    Rajapinta yksityisten ja kunnallisen toimijan tarvitsemien varhaiskasvatustoimijoiden hakuun.
    Query-parametrit:
    *  tyyppi = 'yksityinen' tai 'kunnallinen'
    """
    queryset = VakaJarjestaja.objects.none()
    permission_classes = (IsVardaPaakayttaja, )
    serializer_class = PaosVakaJarjestajaSerializer
    filter_backends = (SearchFilter, )
    search_fields = ['nimi', '=organisaatio_oid', '=y_tunnus']

    def get_queryset(self):
        queryset = VakaJarjestaja.objects.all()
        tyyppi = self.request.query_params.get('tyyppi', None)
        if tyyppi in ['yksityinen', 'kunnallinen']:
            condition = Q(yritysmuoto__in=VakaJarjestaja.get_kuntatyypit())
            queryset = queryset.filter(condition) if tyyppi == 'kunnallinen' else queryset.exclude(condition)
        return queryset.order_by('id')


class NestedToimipaikanLapsetViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn toimipaikan lapset
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.HenkiloNimiFilter
    queryset = Henkilo.objects.none()
    serializer_class = ToimipaikanLapsetUISerializer
    permission_classes = (CustomObjectPermissions,)

    def get_toimipaikka(self, request, toimipaikka_pk=None):
        toimipaikka = get_object_or_404(Toimipaikka.objects.all(), pk=toimipaikka_pk)
        user = request.user
        if not user.has_perm("view_toimipaikka", toimipaikka):
            raise Http404("Not found.")

    def get_lapsi_object_ids_user_has_view_permissions(self):
        model_name = 'lapsi'
        content_type = ContentType.objects.get(model=model_name)
        return get_object_ids_user_has_permissions(self.request.user, model_name, content_type)

    def get_vakapaatokset_in_toimipaikka_queryset(self, *args, **kwargs):
        query_params = self.request.query_params
        filtering_etunimet = query_params.get('etunimet', '')
        filtering_sukunimi = query_params.get('sukunimi', '')
        lapsi_object_ids_user_has_view_permissions = self.get_lapsi_object_ids_user_has_view_permissions()

        vakasuhde_queryset = (Varhaiskasvatussuhde.objects
                              .select_related('varhaiskasvatuspaatos__lapsi__henkilo')
                              .filter(Q(toimipaikka__id=kwargs['toimipaikka_pk']) &
                                      Q(varhaiskasvatuspaatos__lapsi__id__in=lapsi_object_ids_user_has_view_permissions))
                              .order_by('varhaiskasvatuspaatos__lapsi__henkilo__sukunimi',
                                        'varhaiskasvatuspaatos__lapsi__henkilo__etunimet')
                              )
        if filtering_etunimet != '':
            vakasuhde_queryset = vakasuhde_queryset.filter(
                varhaiskasvatuspaatos__lapsi__henkilo__etunimet__icontains=filtering_etunimet)
        if filtering_sukunimi != '':
            vakasuhde_queryset = vakasuhde_queryset.filter(
                varhaiskasvatuspaatos__lapsi__henkilo__sukunimi__icontains=filtering_sukunimi)

        return (vakasuhde_queryset
                .values(etunimet=F('varhaiskasvatuspaatos__lapsi__henkilo__etunimet'),
                        sukunimi=F('varhaiskasvatuspaatos__lapsi__henkilo__sukunimi'),
                        henkilo_oid=F('varhaiskasvatuspaatos__lapsi__henkilo__henkilo_oid'),
                        syntyma_pvm=F('varhaiskasvatuspaatos__lapsi__henkilo__syntyma_pvm'),
                        lapsi_id=F('varhaiskasvatuspaatos__lapsi__id')
                        )
                .distinct('varhaiskasvatuspaatos__lapsi__henkilo__sukunimi',
                          'varhaiskasvatuspaatos__lapsi__henkilo__etunimet',
                          'varhaiskasvatuspaatos__lapsi__id')
                )

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['toimipaikka_pk'].isdigit():
            raise Http404('Not found.')
        self.get_toimipaikka(request, toimipaikka_pk=kwargs['toimipaikka_pk'])

        """
        We can differentiate results based on e.g. user-id, and this is needed since queryset
        can be different for one toimipaikka, depending on user permissions.
        """
        user_id = self.request.user.id
        toimipaikka_cache_key = create_cache_key(user_id, request.get_full_path())
        queryset = cache.get(toimipaikka_cache_key)
        if queryset is None:

            key_for_list_of_all_toimipaikka_cache_keys = 'toimipaikan_lapset_' + kwargs['toimipaikka_pk']
            list_of_all_toimipaikka_cache_keys = cache.get(key_for_list_of_all_toimipaikka_cache_keys)
            if list_of_all_toimipaikka_cache_keys is None:
                list_of_all_toimipaikka_cache_keys = []
            if toimipaikka_cache_key not in list_of_all_toimipaikka_cache_keys:
                list_of_all_toimipaikka_cache_keys.append(toimipaikka_cache_key)
            cache.set(key_for_list_of_all_toimipaikka_cache_keys, list_of_all_toimipaikka_cache_keys, 8 * 60 * 60)

            save_audit_log(request.user, request.get_full_path())
            queryset = self.get_vakapaatokset_in_toimipaikka_queryset(toimipaikka_pk=kwargs['toimipaikka_pk'])
            cache.set(toimipaikka_cache_key, queryset, 8 * 60 * 60)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Pagination is disabled
        serializer = self.get_serializer(queryset.distinct(), many=True)
        return Response(serializer.data)
