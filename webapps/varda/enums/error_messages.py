import enum


def get_error_dict(error_code, error_description):
    return {'error_code': error_code, 'description': error_description}


class ErrorMessages(enum.Enum):
    """
    This enum contains all error messages. New errors should be added here and referenced
    (e.g. ErrorMessages.GE001.value). New errors should also be added to Koodistopalvelu which contains translations
    for the error codes.

    The code contains of a two-character prefix and a three-number code (e.g. XX000).
    If a code is dynamic, e.g. DY001 indicating max_length, the error description has a variable value.
    """
    # General errors, prefix: GE
    GE001 = get_error_dict('GE001', 'This field is required.')
    GE002 = get_error_dict('GE002', 'This field may not be null.')
    GE003 = get_error_dict('GE003', 'This field may not be blank.')
    GE004 = get_error_dict('GE004', 'This field must be a list.')
    GE005 = get_error_dict('GE005', 'This list may not be empty.')
    GE006 = get_error_dict('GE006', 'This field must be a date string in YYYY-MM-DD format.')
    GE007 = get_error_dict('GE007', 'Not a valid choice.')
    GE008 = get_error_dict('GE008', 'Invalid hyperlink, object does not exist.')
    GE009 = get_error_dict('GE009', 'Invalid hyperlink.')
    GE010 = get_error_dict('GE010', 'This field must be an integer.')
    GE011 = get_error_dict('GE011', 'This field must be a boolean.')
    GE012 = get_error_dict('GE012', 'This field must be a number string.')
    GE013 = get_error_dict('GE013', 'Changing of this field is not allowed.')
    GE014 = get_error_dict('GE014', 'No data in request.')
    GE015 = get_error_dict('GE015', 'This field is read only.')
    GE016 = get_error_dict('GE016', 'Problem accessing database.')
    GE017 = get_error_dict('GE017', 'You must give at least one value.')
    GE018 = get_error_dict('GE018', 'Invalid decimal step.')

    # Dynamic errors, prefix: DY
    DY001 = get_error_dict('DY001', 'Ensure this field has no more than {} characters.')
    DY002 = get_error_dict('DY002', 'Ensure this field has at least {} characters.')
    DY003 = get_error_dict('DY003', 'This list should contain no more than {} items.')
    DY004 = get_error_dict('DY004', 'Ensure this value is greater than or equal to {}.')
    DY005 = get_error_dict('DY005', 'Ensure this value is less than or equal to {}.')
    DY006 = get_error_dict('DY006', 'Ensure that there are no more than {} decimal places.')
    DY007 = get_error_dict('DY007', 'Ensure that there are no more than {} digits in total.')
    DY008 = get_error_dict('DY008', 'Request was throttled. Try again in {} seconds.')

    # VakaJarjestaja errors, prefix: VJ
    VJ001 = get_error_dict('VJ001', 'Cannot delete Vakajarjestaja. There are objects referencing it that need to be deleted first.')
    VJ002 = get_error_dict('VJ002', 'yritysmuoto is not one of the permitted values.')
    VJ003 = get_error_dict('VJ003', 'y_tunnus length is incorrect.')
    VJ004 = get_error_dict('VJ004', 'y_tunnus has no hyphen.')
    VJ005 = get_error_dict('VJ005', 'y_tunnus check number cannot be 1.')
    VJ006 = get_error_dict('VJ006', 'y_tunnus has incorrect check number.')
    VJ007 = get_error_dict('VJ007', 'Not a valid IPv4-address.')
    VJ008 = get_error_dict('VJ008', 'Not a valid IPv6-address.')
    VJ009 = get_error_dict('VJ009', 'Not a valid IBAN code.')

    # Toimipaikka errors, prefix: TP
    TP001 = get_error_dict('TP001', 'Combination of nimi and vakajarjestaja fields should be unique.')
    TP002 = get_error_dict('TP002', 'Could not create Toimipaikka in Organisaatiopalvelu.')
    TP003 = get_error_dict('TP003', 'This Toimipaikka should be modified in Organisaatiopalvelu.')
    TP004 = get_error_dict('TP004', 'It is not allowed to change the Vakajarjestaja which Toimipaikka belongs to.')
    TP005 = get_error_dict('TP005', 'It is not allowed to change the toimintamuoto_koodi of a Toimipaikka that has no organisaatio_oid.')
    TP006 = get_error_dict('TP006', 'Toimipaikka with name \'Palveluseteli ja ostopalvelu\' is reserved for system.')
    TP007 = get_error_dict('TP007', 'Could not check duplicates from Organisaatiopalvelu. Please try again later.')
    TP008 = get_error_dict('TP008', 'Toimipaikka with this name already exists in Organisaatiopalvelu.')
    TP009 = get_error_dict('TP009', 'No add-permissions under Vakajarjestaja.')
    TP010 = get_error_dict('TP010', 'alkamis_pvm must be before Toimipaikka paattymis_pvm.')
    TP011 = get_error_dict('TP011', 'alkamis_pvm must be equal to or after Toimipaikka alkamis_pvm.')
    TP012 = get_error_dict('TP012', 'paattymis_pvm must be before or equal to Toimipaikka paattymis_pvm.')
    TP013 = get_error_dict('TP013', 'nimi has disallowed characters.')
    TP014 = get_error_dict('TP014', 'nimi must have at least 2 characters.')
    TP015 = get_error_dict('TP015', 'No more than 2 consecutively repeating special characters are allowed.')
    TP016 = get_error_dict('TP016', 'nimi is not in the correct format.')

    # ToiminnallinenPainotus errors, prefix: TO
    TO001 = get_error_dict('TO001', 'ToiminnallinenPainotus with this toimintapainotus_koodi already exists for toimipaikka on the given date range.')

    # KieliPainotus errors, prefix: KP
    KP001 = get_error_dict('KP001', 'KieliPainotus with this kielipainotus_koodi already exists for toimipaikka on the given date range.')

    # Henkilo errors, prefix: HE
    HE001 = get_error_dict('HE001', 'Person data does not match with the entered data.')
    HE002 = get_error_dict('HE002', 'Unfortunately this Henkilo cannot be added. Is the Henkilo yksiloity?')
    HE003 = get_error_dict('HE003', 'Not found.')
    HE004 = get_error_dict('HE004', 'Either henkilotunnus or henkilo_oid is needed, but not both.')
    HE005 = get_error_dict('HE005', 'Incorrect henkilotunnus length.')
    HE006 = get_error_dict('HE006', 'Incorrect century character.')
    HE007 = get_error_dict('HE007', 'Incorrect henkilotunnus date.')
    HE008 = get_error_dict('HE008', 'ID number or control character is incorrect.')
    HE009 = get_error_dict('HE009', 'Temporary henkilotunnus is not permitted.')
    HE010 = get_error_dict('HE010', 'kutsumanimi must be one name.')
    HE011 = get_error_dict('HE011', 'kutsumanimi is not valid.')
    HE012 = get_error_dict('HE012', 'Name has disallowed characters.')
    HE013 = get_error_dict('HE013', 'Name is not in the correct format.')

    # Lapsi errors, prefix: LA
    LA001 = get_error_dict('LA001', 'Error while creating Lapsi.')
    LA002 = get_error_dict('LA002', 'User does not have permissions for provided vakatoimija.')
    LA003 = get_error_dict('LA003', 'Cannot delete Lapsi. There are Maksutieto objects referencing it that need to be deleted first.')
    LA004 = get_error_dict('LA004', 'Cannot delete Lapsi. There are objects referencing it that need to be deleted first.')
    LA005 = get_error_dict('LA005', 'Either vakatoimija or oma_organisaatio and paos_organisaatio are required.')
    LA006 = get_error_dict('LA006', 'Lapsi cannot be PAOS and regular at the same time.')
    LA007 = get_error_dict('LA007', 'For PAOS, both oma_organisaatio and paos_organisaatio are required.')
    LA008 = get_error_dict('LA008', 'oma_organisaatio cannot be same as paos_organisaatio.')

    # Varhaiskasvatuspaatos errors, prefix: VP
    VP001 = get_error_dict('VP001', 'hakemus_pvm must be before or equal to alkamis_pvm.')
    VP002 = get_error_dict('VP002', 'Varhaiskasvatussuhde alkamis_pvm must be equal to or after Varhaiskasvatuspaatos alkamis_pvm.')
    VP003 = get_error_dict('VP003', 'Varhaiskasvatuspaatos paattymis_pvm must be equal to or after Varhaiskasvatussuhde paattymis_pvm.')
    VP004 = get_error_dict('VP004', 'Cannot delete Varhaiskasvatuspaatos. There are objects referencing it that need to be deleted first.')
    VP005 = get_error_dict('VP005', 'Invalid code for PAOS Lapsi.')
    VP006 = get_error_dict('VP006', 'Invalid code for non-PAOS Lapsi.')
    VP007 = get_error_dict('VP007', 'Invalid code for kunnallinen Lapsi.')
    VP008 = get_error_dict('VP008', 'Invalid code for yksityinen Lapsi.')
    VP009 = get_error_dict('VP009', 'paivittainen_vaka_kytkin must be given if vuorohoito_kytkin is false.')
    VP010 = get_error_dict('VP010', 'kokopaivainen_vaka_kytkin must be given if vuorohoito_kytkin is false.')
    VP011 = get_error_dict('VP011', 'Lapsi already has 3 overlapping Varhaiskasvatuspaatos on the given date range.')

    # Varhaiskasvatussuhde errors, prefix: VS
    VS001 = get_error_dict('VS001', 'This Lapsi is already under another Vakajarjestaja. Please create a new one.')
    VS002 = get_error_dict('VS002', 'organisaatio_oid missing for Vakajarjestaja.')
    VS003 = get_error_dict('VS003', 'Changing of varhaiskasvatuspaatos is not allowed.')
    VS004 = get_error_dict('VS004', 'Changing of toimipaikka is not allowed.')
    VS005 = get_error_dict('VS005', 'Vakajarjestaja is different than paos_organisaatio for Lapsi.')
    VS006 = get_error_dict('VS006', 'jarjestamismuoto_koodi is invalid for Toimipaikka.')
    VS007 = get_error_dict('VS007', 'jarjestamismuoto_koodi is invalid for kunnallinen Toimipaikka.')
    VS008 = get_error_dict('VS008', 'jarjestamismuoto_koodi is invalid for yksityinen Toimipaikka.')
    VS009 = get_error_dict('VS009', 'Varhaiskasvatussuhde alkamis_pvm cannot be same or after Toimipaikka paattymis_pvm.')
    VS010 = get_error_dict('VS010', 'Varhaiskasvatussuhde paattymis_pvm cannot be after Toimipaikka paattymis_pvm.')
    VS011 = get_error_dict('VS011', 'Varhaiskasvatussuhde alkamis_pvm must be before or equal to Varhaiskasvatuspaatos paattymis_pvm.')
    VS012 = get_error_dict('VS012', 'Varhaiskasvatussuhde must have paattymis_pvm because Varhaiskasvatuspaatos has paattymis_pvm.')
    VS013 = get_error_dict('VS013', 'Lapsi already has 3 overlapping Varhaiskasvatussuhde on the given date range.')

    # Maksutieto errors, prefix: MA
    MA001 = get_error_dict('MA001', 'perheen_koko field is required.')
    MA002 = get_error_dict('MA002', 'huoltajat field is required.')
    MA003 = get_error_dict('MA003', 'No matching huoltaja found.')
    MA004 = get_error_dict('MA004', 'Lapsi already has 2 overlapping Maksutieto on the given date range.')
    MA005 = get_error_dict('MA005', 'Maksutieto alkamis_pvm must be equal to or after earliest Varhaiskasvatuspaatos alkamis_pvm.')
    MA006 = get_error_dict('MA006', 'Maksutieto alkamis_pvm must be before or equal to latest Varhaiskasvatuspaatos paattymis_pvm.')
    MA007 = get_error_dict('MA007', 'Maksutieto paattymis_pvm must be before or equal to latest Varhaiskasvatuspaatos paattymis_pvm.')
    MA008 = get_error_dict('MA008', 'Lapsi does not have Varhaiskasvatuspaatos. Add Varhaiskasvatuspaatos before adding Maksutieto.')
    MA009 = get_error_dict('MA009', 'Lapsi does not have Varhaiskasvatussuhde. Add Varhaiskasvatussuhde before adding Maksutieto.')
    MA010 = get_error_dict('MA010', 'User does not have permissions to add Maksutieto for this Lapsi.')
    MA011 = get_error_dict('MA011', 'Maximum number of huoltajat is 7.')
    MA012 = get_error_dict('MA012', 'Duplicated henkilotunnus given.')
    MA013 = get_error_dict('MA013', 'Duplicated henkilo_oid given.')
    MA014 = get_error_dict('MA014', 'paattymis_pvm must be equal to or after 2020-09-01 for yksityinen Lapsi.')

    # PaosToiminta errors, prefix: PT
    PT001 = get_error_dict('PT001', 'oma_organisaatio cannot be the same as paos_organisaatio.')
    PT002 = get_error_dict('PT002', 'paos_toimipaikka cannot be in oma_organisaatio.')
    PT003 = get_error_dict('PT003', 'jarjestamismuoto_koodi is not jm02 or jm03.')
    PT004 = get_error_dict('PT004', 'Combination of oma_organisaatio and paos_organisaatio fields should be unique.')
    PT005 = get_error_dict('PT005', 'Combination of oma_organisaatio and paos_toimipaikka fields should be unique.')
    PT006 = get_error_dict('PT006', 'Either paos_organisaatio or paos_toimipaikka is needed, not both.')
    PT007 = get_error_dict('PT007', 'Either paos_organisaatio or paos_toimipaikka is needed.')
    PT008 = get_error_dict('PT008', 'paos_organisaatio must be kunta or kuntayhtyma.')
    PT009 = get_error_dict('PT009', 'Vakajarjestaja must have organisaatio_oid.')
    PT010 = get_error_dict('PT010', 'There is no active PaosToiminta to this Toimipaikka.')

    # PaosOikeus errors, prefix: PO
    PO001 = get_error_dict('PO001', 'tallentaja_organisaatio must be either jarjestaja_kunta_organisaatio or tuottaja_organisaatio.')
    PO002 = get_error_dict('PO002', 'tallentaja_organisaatio is already the same as requested.')
    PO003 = get_error_dict('PO003', 'There is no active PaosOikeus.')

    # Tyontekija errors, prefix: TY
    TY001 = get_error_dict('TY001', 'Cannot delete Tyontekija. There are Tutkinto objects referencing it that need to be deleted first.')
    TY002 = get_error_dict('TY002', 'Cannot delete Tyontekija. There are objects referencing it that need to be deleted first.')
    TY003 = get_error_dict('TY003', 'This Henkilo is already referenced by Lapsi objects.')
    TY004 = get_error_dict('TY004', 'Changing of vakajarjestaja is not allowed.')
    TY005 = get_error_dict('TY005', 'Combination of henkilo and vakajarjestaja fields should be unique.')

    # Tutkinto errors, prefix: TU
    TU001 = get_error_dict('TU001', 'Cannot delete Tutkinto. There are Palvelussuhde objects referencing it that need to be deleted first.')
    TU002 = get_error_dict('TU002', 'Given Vakajarjestaja has not added this Henkilo as Tyontekija.')
    TU003 = get_error_dict('TU003', 'Given Toimipaikka is not matching provided Vakajarjestaja.')

    # Palvelussuhde errors, prefix: PS
    PS001 = get_error_dict('PS001', 'Cannot delete Palvelussuhde. There are objects referencing it that need to be deleted first.')
    PS002 = get_error_dict('PS002', 'Modify actions requires permissions to all Tyoskentelypaikka objects.')
    PS003 = get_error_dict('PS003', 'paattymis_pvm is required for tyosuhde_koodi 2.')
    PS004 = get_error_dict('PS004', 'Tyontekija has Tutkinto objects other than just 003.')
    PS005 = get_error_dict('PS005', 'Tyontekija does not have the given Tutkinto.')
    PS006 = get_error_dict('PS006', 'Tyontekija already has 7 overlapping Palvelussuhde on the given date range.')
    PS007 = get_error_dict('PS007', 'paattymis_pvm must be equal to or after 2020-09-01.')

    # Tyoskentelypaikka errors, prefix: TA
    TA001 = get_error_dict('TA001', 'Vakajarjestaja level permissions required for kiertava tyontekija.')
    TA002 = get_error_dict('TA002', 'Cannot delete Tyoskentelypaikka. Taydennyskoulutus objects with this tehtavanimike_koodi must be deleted first.')
    TA003 = get_error_dict('TA003', 'Cannot delete Tyoskentelypaikka. There are objects referencing it that need to be deleted first.')
    TA004 = get_error_dict('TA004', 'Toimipaikka cannot be specified with kiertava_tyontekija_kytkin.')
    TA005 = get_error_dict('TA005', 'Toimipaikka must have the same Vakajarjestaja as Tyontekija.')
    TA006 = get_error_dict('TA006', 'paattymis_pvm must be before or equal to Palvelussuhde paattymis_pvm.')
    TA007 = get_error_dict('TA007', 'paattymis_pvm must be equal to or after 2020-09-01.')
    TA008 = get_error_dict('TA008', 'alkamis_pvm must be equal to or after Palvelussuhde alkamis_pvm.')
    TA009 = get_error_dict('TA009', 'alkamis_pvm must be before or equal to Palvelussuhde paattymis_pvm.')
    TA010 = get_error_dict('TA010', 'Cannot have different values of kiertava_tyontekija_kytkin on overlapping date ranges.')
    TA011 = get_error_dict('TA011', 'Palvelussuhde already has 3 overlapping Tyoskentelypaikka on the given date range.')
    TA012 = get_error_dict('TA012', 'toimipaikka is required if kiertava_tyontekija_kytkin is false.')
    TA013 = get_error_dict('TA013', 'Tyoskentelypaikka must have paattymis_pvm because Palvelussuhde has paattymis_pvm.')

    # PidempiPoissaolo errors, prefix: PP
    PP001 = get_error_dict('PP001', 'Cannot delete PidempiPoissaolo. There are objects referencing it that need to be deleted first.')
    PP002 = get_error_dict('PP002', 'No matching Tyoskentelypaikka exists.')
    PP003 = get_error_dict('PP003', 'Poissaolo duration must be 60 days or more.')
    PP004 = get_error_dict('PP004', 'paattymis_pvm must be before or equal to Palvelussuhde paattymis_pvm.')
    PP005 = get_error_dict('PP005', 'alkamis_pvm must be equal to or after Palvelussuhde alkamis_pvm.')
    PP006 = get_error_dict('PP006', 'alkamis_pvm must be before Palvelussuhde paattymis_pvm.')
    PP007 = get_error_dict('PP007', 'Palvelussuhde already has 1 overlapping PidempiPoissaolo on the given date range.')
    PP008 = get_error_dict('PP008', 'paattymis_pvm must be equal to or after 2020-09-01.')

    # TilapainenHenkilosto errors, prefix: TH
    TH001 = get_error_dict('TH001', 'TilapainenHenkilosto already exists for this month.')
    TH002 = get_error_dict('TH002', 'kuukausi must be equal to or after Vakajarjestaja alkamis_pvm.')
    TH003 = get_error_dict('TH003', 'kuukausi must be before or equal to Vakajarjestaja paattymis_pvm.')
    TH004 = get_error_dict('TH004', 'tuntimaara cannot be zero if tyontekijamaara is greater than zero.')
    TH005 = get_error_dict('TH005', 'tyontekijamaara cannot be zero if tuntimaara is greater than zero.')
    TH006 = get_error_dict('TH006', 'kuukausi must be in the past.')

    # Taydennyskoulutus errors, prefix: TK
    TK001 = get_error_dict('TK001', 'Tyontekija not specified. Use (tyontekija), (henkilo_oid, vakajarjestaja_oid) or (lahdejarjestelma, tunniste).')
    TK002 = get_error_dict('TK002', 'Either both henkilo_oid and vakajarjestaja_oid, or neither must be given.')
    TK003 = get_error_dict('TK003', 'Either both lahdejarjestelma and tunniste, or neither must be given.')
    TK004 = get_error_dict('TK004', 'Could not find Tyontekija matching the given (henkilo_oid, vakajarjestaja_oid).')
    TK005 = get_error_dict('TK005', 'henkilo_oid does not refer to the same Tyontekija as URL.')
    TK006 = get_error_dict('TK006', 'Could not find Tyontekija matching the given (lahdejarjestelma, tunniste).')
    TK007 = get_error_dict('TK007', 'Tunniste does not refer to the same Tyontekija as URL or henkilo_oid.')
    TK008 = get_error_dict('TK008', 'Tyontekija does not have given tehtavanimike_koodi.')
    TK009 = get_error_dict('TK009', 'taydennyskoulutus_tyontekijat_add and taydennyskoulutus_tyontekijat_remove fields cannot be used '
                                    'if taydennyskoulutus_tyontekijat is provided.')
    TK010 = get_error_dict('TK010', 'Duplicates detected.')
    TK011 = get_error_dict('TK011', 'Tyontekija cannot have same Taydennyskoulutus more than once.')
    TK012 = get_error_dict('TK012', 'Tyontekija must have this Taydennyskoulutus.')
    TK013 = get_error_dict('TK013', 'Cannot delete all Tyontekija objects from Taydennyskoulutus.')
    TK014 = get_error_dict('TK014', 'Insufficient permissions to Taydennyskoulutus related Tyontekija objects.')
    TK015 = get_error_dict('TK015', 'suoritus_pvm must be equal to or after 2020-09-01.')

    # Permission/Authentication errors, prefix: PE
    PE001 = get_error_dict('PE001', 'User does not have permissions to change this object.')
    PE002 = get_error_dict('PE002', 'User does not have permissions to delete this object.')
    PE003 = get_error_dict('PE003', 'User does not have permissions.')
    PE004 = get_error_dict('PE004', 'User does not have Paakayttaja permissions.')
    PE005 = get_error_dict('PE005', 'Authentication credentials were not provided.')
    PE006 = get_error_dict('PE006', 'User does not have permission to perform this action.')
    PE007 = get_error_dict('PE007', 'User authentication failed.')
    PE008 = get_error_dict('PE008', 'User does not have permissions to just one active organization.')

    # Admin errors, prefix: AD
    AD001 = get_error_dict('AD001', 'Incorrect data format. ID should be a positive integer.')
    AD002 = get_error_dict('AD002', 'User was not found with this ID.')
    AD003 = get_error_dict('AD003', 'User with this ID is not a CAS user.')
    AD004 = get_error_dict('AD004', 'User with this ID is not in oph_staff group.')
    AD005 = get_error_dict('AD005', 'You must approve with yes.')

    # Localisation errors, prefix: LO
    LO001 = get_error_dict('LO001', 'category URL parameter is required.')
    LO002 = get_error_dict('LO002', 'locale URL parameter must be either FI or SV.')

    # RelatedField errors, prefix: RF
    RF001 = get_error_dict('RF001', 'Either this field or the parent field is required.')
    RF002 = get_error_dict('RF002', 'Could not parse object ID from parent field.')
    RF003 = get_error_dict('RF003', 'Could not find matching object.')
    RF004 = get_error_dict('RF004', 'Differs from parent field.')

    # Koodisto errors, prefix: KO
    KO001 = get_error_dict('KO001', 'Code cannot have spaces.')
    KO002 = get_error_dict('KO002', 'Code cannot have special characters.')
    KO003 = get_error_dict('KO003', 'Not a valid code.')
    KO004 = get_error_dict('KO004', 'Problem with Koodistopalvelu.')

    # Miscellaneous errors, prefix: MI
    MI001 = get_error_dict('MI001', 'Token was not refreshed.')
    MI002 = get_error_dict('MI002', 'Organisaatio_oid(s) missing.')
    MI003 = get_error_dict('MI003', 'paattymis_pvm must be after alkamis_pvm.')
    MI004 = get_error_dict('MI004', 'paattymis_pvm must be equal to or after alkamis_pvm.')
    MI005 = get_error_dict('MI005', 'Postinumero is incorrect.')
    MI006 = get_error_dict('MI006', 'Not a valid Finnish phone number.')
    MI007 = get_error_dict('MI007', 'Number of OID sections is incorrect.')
    MI008 = get_error_dict('MI008', 'OPH part of OID is incorrect.')
    MI009 = get_error_dict('MI009', 'OID is incorrect.')
    MI010 = get_error_dict('MI010', 'Not an OID for an organization.')
    MI011 = get_error_dict('MI011', 'Not an OID for a person.')
    MI012 = get_error_dict('MI012', 'Not a valid tunniste.')
    MI013 = get_error_dict('MI013', 'Combination of lahdejarjestelma and tunniste fields should be unique.')
    MI014 = get_error_dict('MI014', 'This date must be equal to or after 2000-01-01.')
    MI015 = get_error_dict('MI015', 'Not found.')
    MI016 = get_error_dict('MI016', 'A server error occurred. Team is investigating this.')
