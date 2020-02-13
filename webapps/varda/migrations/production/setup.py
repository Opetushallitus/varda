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
        'add_ohjaajasuhde',
        'change_ohjaajasuhde',
        'delete_ohjaajasuhde',
        'view_ohjaajasuhde',
        'add_taydennyskoulutus',
        'change_taydennyskoulutus',
        'delete_taydennyskoulutus',
        'view_taydennyskoulutus',
        'add_toiminnallinenpainotus',
        'change_toiminnallinenpainotus',
        'delete_toiminnallinenpainotus',
        'view_toiminnallinenpainotus',
        'add_toimipaikka',
        'change_toimipaikka',
        'view_toimipaikka',
        'add_tyontekija',
        'change_tyontekija',
        'delete_tyontekija',
        'view_tyontekija',
        'view_vakajarjestaja',
        'change_vakajarjestaja',
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
    toimipaikka_tallentaja.remove('change_vakajarjestaja')
    toimipaikka_tallentaja.remove('add_toimipaikka')
    return toimipaikka_tallentaja


def get_vakajarjestaja_palvelukayttaja_permissions():
    vaka_tallentaja_permissions = get_vaka_tallentaja_permissions()
    vakajarjestaja_palvelukayttaja_permissions = vaka_tallentaja_permissions.copy()
    vakajarjestaja_palvelukayttaja_permissions.extend(get_huoltajatiedot_tallentaja_permissions())  # palvelukayttaja: vakatiedot + huoltajatiedot
    return vakajarjestaja_palvelukayttaja_permissions


def load_initial_permissions():
    from django.contrib.auth.models import Group, Permission
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

    for group_tuple in group_permission_array:
        group_obj = Group.objects.create(name=group_tuple[0])
        group_permissions = Permission.objects.filter(codename__in=group_tuple[1])
        group_obj.permissions.add(*group_permissions)


def load_huoltajatiedot_permissions():
    from django.contrib.auth.models import Group, Permission
    huoltajatiedot_tallentaja_permissions = get_huoltajatiedot_tallentaja_permissions()
    huoltajatiedot_katselija_permissions = get_huoltajatiedot_katselija_permissions()

    group_permission_array = [
        ('vakajarjestaja_huoltajatiedot_tallentaja', huoltajatiedot_tallentaja_permissions),
        ('vakajarjestaja_huoltajatiedot_katselija', huoltajatiedot_katselija_permissions),
        ('toimipaikka_huoltajatiedot_tallentaja', huoltajatiedot_tallentaja_permissions),
        ('toimipaikka_huoltajatiedot_katselija', huoltajatiedot_katselija_permissions)
    ]

    for group_tuple in group_permission_array:
        group_obj = Group.objects.create(name=group_tuple[0])
        group_permissions = Permission.objects.filter(codename__in=group_tuple[1])
        group_obj.permissions.add(*group_permissions)


def load_paos_permissions():
    from django.contrib.auth.models import Group, Permission
    vakajarjestaja_paakayttaja_permissions = get_vakajarjestaja_paakayttaja_permissions()
    group_permission_array = [
        ('vakajarjestaja_paakayttaja', vakajarjestaja_paakayttaja_permissions)
    ]
    for group_tuple in group_permission_array:
        group_obj = Group.objects.create(name=group_tuple[0])
        group_permissions = Permission.objects.filter(codename__in=group_tuple[1])
        group_obj.permissions.add(*group_permissions)


def load_initial_users():
    from django.contrib.auth.models import User
    User.objects.create(username='credadmin',
                        password='pbkdf2_sha256$150000$ikCYVXfbE0rM$Nlh+fJ8CHNOI4tSFyOwdraKoLlv+XT8BjHNWKr6Nlic=',
                        is_superuser=True,
                        is_staff=True)


def load_initial_data():
    load_initial_permissions()
    load_initial_users()


def load_paos_data():
    load_paos_permissions()
