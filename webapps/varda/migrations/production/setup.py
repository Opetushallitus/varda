import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)


def get_vaka_tallentaja_permissions():
    return [
        'add_henkilo',
        'view_henkilo',
        'add_kielipainotus',
        'add_kielipainotus',
        'change_kielipainotus',
        'delete_kielipainotus',
        'view_kielipainotus',
        'add_lapsi',
        'change_lapsi',
        'delete_lapsi',
        'view_lapsi',
        'add_toiminnallinenpainotus',
        'change_toiminnallinenpainotus',
        'delete_toiminnallinenpainotus',
        'view_toiminnallinenpainotus',
        'add_toimipaikka',
        'change_toimipaikka',
        'view_toimipaikka',
        'view_vakajarjestaja',
        'add_varhaiskasvatuspaatos',
        'change_varhaiskasvatuspaatos',
        'delete_varhaiskasvatuspaatos',
        'view_varhaiskasvatuspaatos',
        'add_varhaiskasvatussuhde',
        'change_varhaiskasvatussuhde',
        'delete_varhaiskasvatussuhde',
        'view_varhaiskasvatussuhde'
    ]


def get_huoltajatiedot_tallentaja_permissions():
    return [
        'add_maksutieto',
        'change_maksutieto',
        'delete_maksutieto',
        'view_maksutieto',
        'view_vakajarjestaja',
        'view_toimipaikka',
        'view_kielipainotus',
        'view_toiminnallinenpainotus',
        'view_lapsi'
    ]


def get_huoltajatiedot_katselija_permissions():
    return [
        'view_maksutieto',
        'view_vakajarjestaja',
        'view_toimipaikka',
        'view_kielipainotus',
        'view_toiminnallinenpainotus',
        'view_lapsi'
    ]


def get_tyontekija_tallentaja_permissions():
    return [
        'add_henkilo',
        'view_henkilo',
        'add_tyontekija',
        'change_tyontekija',
        'delete_tyontekija',
        'view_tyontekija',
        'add_tyoskentelypaikka',
        'change_tyoskentelypaikka',
        'delete_tyoskentelypaikka',
        'view_tyoskentelypaikka',
        'add_palvelussuhde',
        'change_palvelussuhde',
        'delete_palvelussuhde',
        'view_palvelussuhde',
        'add_pidempipoissaolo',
        'change_pidempipoissaolo',
        'delete_pidempipoissaolo',
        'view_pidempipoissaolo',
        'add_tutkinto',
        'change_tutkinto',
        'delete_tutkinto',
        'view_tutkinto',
        'view_vakajarjestaja',
        'view_toimipaikka',
    ]


def get_tyontekija_katselija_permissions():
    return [
        'view_henkilo',
        'view_tyontekija',
        'view_tyoskentelypaikka',
        'view_palvelussuhde',
        'view_pidempipoissaolo',
        'view_tutkinto',
        'view_vakajarjestaja',
        'view_toimipaikka',
    ]


def get_taydennyskoulutus_tallentaja_permissions():
    return [
        'add_taydennyskoulutus',
        'change_taydennyskoulutus',
        'delete_taydennyskoulutus',
        'view_taydennyskoulutus',
        'view_vakajarjestaja',
        'view_toimipaikka',
    ]


def get_taydennyskoulutus_katselija_permissions():
    return [
        'view_taydennyskoulutus',
        'view_vakajarjestaja',
        'view_toimipaikka',
    ]


def get_tilapainen_henkilosto_tallentaja_permissions():
    return [
        'add_tilapainenhenkilosto',
        'change_tilapainenhenkilosto',
        'delete_tilapainenhenkilosto',
        'view_tilapainenhenkilosto',
        'view_vakajarjestaja',
    ]


def get_tilapainen_henkilosto_katselija_permissions():
    return [
        'view_tilapainenhenkilosto',
        'view_vakajarjestaja',
    ]


def get_toimijatiedot_katselija_permissions():
    return [
        'view_vakajarjestaja'
    ]


def get_toimijatiedot_tallentaja_permissions():
    return [
        'view_vakajarjestaja',
        'change_vakajarjestaja'
    ]


def get_raporttien_katselija_permissions():
    return [
        'view_vakajarjestaja'
    ]


def get_vakajarjestaja_katselija_permissions():
    vakajarjestaja_tallentaja = get_vaka_tallentaja_permissions()
    vakajarjestaja_katselija = []
    for permission in vakajarjestaja_tallentaja:
        if permission.startswith('view_'):
            vakajarjestaja_katselija.append(permission)
    return vakajarjestaja_katselija


def get_vakajarjestaja_paakayttaja_permissions():
    vakajarjestaja_paakayttaja = get_vakajarjestaja_katselija_permissions()
    paos_permissions = ['view_paostoiminta', 'add_paostoiminta', 'delete_paostoiminta', 'view_paosoikeus', 'change_paosoikeus']
    for permission in paos_permissions:
        vakajarjestaja_paakayttaja.append(permission)
    return vakajarjestaja_paakayttaja


def get_toimipaikka_tallentaja_permissions():
    vakajarjestaja_tallentaja = get_vaka_tallentaja_permissions()
    toimipaikka_tallentaja = vakajarjestaja_tallentaja.copy()
    toimipaikka_tallentaja.remove('add_toimipaikka')
    return toimipaikka_tallentaja


def get_vakajarjestaja_palvelukayttaja_permissions():
    vaka_tallentaja_permissions = get_vaka_tallentaja_permissions()
    vakajarjestaja_palvelukayttaja_permissions = vaka_tallentaja_permissions.copy()
    vakajarjestaja_palvelukayttaja_permissions.extend(get_huoltajatiedot_tallentaja_permissions())  # palvelukayttaja: vakatiedot + huoltajatiedot
    return vakajarjestaja_palvelukayttaja_permissions


def _create_groups_with_permissions(group_tuple_list):
    """
    Creates Groups and assigns given permissions to them
    :param group_tuple_list: List of tuples, e.g. [('group_name', [group_permissions])]
    """
    from django.contrib.auth.models import Group, Permission
    from django.db import IntegrityError

    for group_tuple in group_tuple_list:
        try:
            group_obj = Group.objects.create(name=group_tuple[0])
            group_permissions = Permission.objects.filter(codename__in=group_tuple[1])
            group_obj.permissions.add(*group_permissions)
        except IntegrityError:
            logger.warning('Could not create group {}. Already exists?'.format(group_tuple[0]))


def create_initial_template_groups():
    vakajarjestaja_tallentaja_permissions = get_vaka_tallentaja_permissions()
    vakajarjestaja_palvelukayttaja_permissions = get_vakajarjestaja_palvelukayttaja_permissions()
    vakajarjestaja_katselija_permissions = get_vakajarjestaja_katselija_permissions()
    toimipaikka_tallentaja_permissions = get_toimipaikka_tallentaja_permissions()
    toimipaikka_katselija_permissions = vakajarjestaja_katselija_permissions.copy()
    vakajarjestaja_view_henkilo_permissions = ['view_henkilo']
    oph_staff_permissions = []

    group_permission_array = [
        ('vakajarjestaja_palvelukayttaja', vakajarjestaja_palvelukayttaja_permissions),
        ('vakajarjestaja_tallentaja', vakajarjestaja_tallentaja_permissions),
        ('vakajarjestaja_katselija', vakajarjestaja_katselija_permissions),
        ('toimipaikka_tallentaja', toimipaikka_tallentaja_permissions),
        ('toimipaikka_katselija', toimipaikka_katselija_permissions),
        ('vakajarjestaja_view_henkilo', vakajarjestaja_view_henkilo_permissions),
        ('oph_staff', oph_staff_permissions)
    ]

    _create_groups_with_permissions(group_permission_array)


def create_huoltajatiedot_template_groups():
    huoltajatiedot_tallentaja_permissions = get_huoltajatiedot_tallentaja_permissions()
    huoltajatiedot_katselija_permissions = get_huoltajatiedot_katselija_permissions()

    group_permission_array = [
        ('vakajarjestaja_huoltajatiedot_tallentaja', huoltajatiedot_tallentaja_permissions),
        ('vakajarjestaja_huoltajatiedot_katselija', huoltajatiedot_katselija_permissions),
        ('toimipaikka_huoltajatiedot_tallentaja', huoltajatiedot_tallentaja_permissions),
        ('toimipaikka_huoltajatiedot_katselija', huoltajatiedot_katselija_permissions)
    ]

    _create_groups_with_permissions(group_permission_array)


def clear_old_permissions():
    from django.db.models import Q
    from django.contrib.auth.models import Permission
    # Remove any henkilosto permissions assigned to groups previously
    henkilosto_permissions = Permission.objects.filter(Q(codename__endswith='taydennyskoulutus') |
                                                       Q(codename__endswith='tyontekija') |
                                                       Q(codename__endswith='ohjaajasuhde')
                                                       )
    [henkilosto_permission.group_set.clear() for henkilosto_permission in henkilosto_permissions]


def create_henkilosto_template_groups():
    tyontekija_tallentaja_permissions = get_tyontekija_tallentaja_permissions()
    tyontekija_katselija_permissions = get_tyontekija_katselija_permissions()
    tilapainen_henkilosto_tallentaja_permissions = get_tilapainen_henkilosto_tallentaja_permissions()
    tilapainen_henkilosto_katselija_permissions = get_tilapainen_henkilosto_katselija_permissions()
    taydennyskoulutus_tallentaja_permissions = get_taydennyskoulutus_tallentaja_permissions()
    taydennyskoulutus_katselija_permissions = get_taydennyskoulutus_katselija_permissions()

    group_permission_array = [
        ('vakajarjestaja_henkilosto_tyontekija_tallentaja', tyontekija_tallentaja_permissions),
        ('vakajarjestaja_henkilosto_tyontekija_katselija', tyontekija_katselija_permissions),
        ('vakajarjestaja_henkilosto_tilapainen_tallentaja', tilapainen_henkilosto_tallentaja_permissions),
        ('vakajarjestaja_henkilosto_tilapainen_katselija', tilapainen_henkilosto_katselija_permissions),
        ('vakajarjestaja_henkilosto_taydennyskoulutus_tallentaja', taydennyskoulutus_tallentaja_permissions),
        ('vakajarjestaja_henkilosto_taydennyskoulutus_katselija', taydennyskoulutus_katselija_permissions),
        ('toimipaikka_henkilosto_tyontekija_tallentaja', tyontekija_tallentaja_permissions),
        ('toimipaikka_henkilosto_tyontekija_katselija', tyontekija_katselija_permissions),
        ('toimipaikka_henkilosto_taydennyskoulutus_tallentaja', taydennyskoulutus_tallentaja_permissions),
        ('toimipaikka_henkilosto_taydennyskoulutus_katselija', taydennyskoulutus_katselija_permissions),
    ]

    _create_groups_with_permissions(group_permission_array)


def create_paos_template_groups():
    vakajarjestaja_paakayttaja_permissions = get_vakajarjestaja_paakayttaja_permissions()
    group_permission_array = [
        ('vakajarjestaja_paakayttaja', vakajarjestaja_paakayttaja_permissions)
    ]

    _create_groups_with_permissions(group_permission_array)


def create_toimijatiedot_template_groups():
    toimijatiedot_katselija_permissions = get_toimijatiedot_katselija_permissions()
    toimijatiedot_tallentaja_permissions = get_toimijatiedot_tallentaja_permissions()

    group_permission_list = [
        ('vakajarjestaja_toimijatiedot_katselija', toimijatiedot_katselija_permissions),
        ('vakajarjestaja_toimijatiedot_tallentaja', toimijatiedot_tallentaja_permissions)
    ]

    _create_groups_with_permissions(group_permission_list)


def create_raportit_template_groups():
    raporttien_katselija_permissions = get_raporttien_katselija_permissions()
    group_permissions_list = [
        ('vakajarjestaja_raporttien_katselija', raporttien_katselija_permissions)
    ]
    _create_groups_with_permissions(group_permissions_list)


def load_initial_users():
    from django.contrib.auth.models import User
    User.objects.create(username='credadmin',
                        password='pbkdf2_sha256$150000$ikCYVXfbE0rM$Nlh+fJ8CHNOI4tSFyOwdraKoLlv+XT8BjHNWKr6Nlic=',
                        is_superuser=True,
                        is_staff=True)


def load_initial_data():
    create_initial_template_groups()
    load_initial_users()


def load_paos_data():
    create_paos_template_groups()


def modify_change_vakajarjestaja_permission():
    """
    Removes change_vakajarjestaja permission from VARDA-TALLENTAJA groups. Also modifies all object level permissions.
    """
    from django.contrib.auth.models import Group, Permission
    from django.db.models import Q
    from guardian.shortcuts import remove_perm
    from varda.models import VakaJarjestaja, Z4_CasKayttoOikeudet
    from varda.permission_groups import get_permission_group

    permission_name = 'change_vakajarjestaja'
    change_vakajarjestaja_permission = Permission.objects.get(codename=permission_name)

    # Remove the permission from tallentaja template group
    tallentaja_group_qs = Group.objects.filter(Q(name='vakajarjestaja_tallentaja') &
                                               Q(permissions__codename=permission_name))
    if tallentaja_group_qs.exists():
        tallentaja_group_qs.first().permissions.remove(change_vakajarjestaja_permission)

    # Go through each vakajarjestaja with OID and modify TALLENTAJA permissions
    vakajarjestaja_qs = VakaJarjestaja.objects.exclude(Q(organisaatio_oid__isnull=True) | Q(organisaatio_oid=''))
    for vakajarjestaja in vakajarjestaja_qs:
        tallentaja_group = get_permission_group(Z4_CasKayttoOikeudet.TALLENTAJA, vakajarjestaja.organisaatio_oid)
        if tallentaja_group:
            # Remove permission from the TALLENTAJA group and from the vakajarjestaja object
            remove_perm(permission_name, tallentaja_group, vakajarjestaja)
