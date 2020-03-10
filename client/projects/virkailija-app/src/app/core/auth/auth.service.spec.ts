import {TestBed} from '@angular/core/testing';

import {AuthService} from './auth.service';
import {VardaApiService} from '../services/varda-api.service';
import {CookieService} from 'ngx-cookie-service';
import {Router} from '@angular/router';
import {vakajarjestajatStub} from '../../shared/testmocks/vakajarjestajat-stub';
import {VardaVakajarjestajaService} from '../services/varda-vakajarjestaja.service';
import {toimipaikatStub} from '../../shared/testmocks/toimipaikat-stub';
import {VardaKayttooikeusRoles} from '../../utilities/varda-kayttooikeus-roles';
import {HttpService} from 'varda-shared';

describe('AuthService', () => {

  let vardaAuthService: AuthService;
  let vardaApiService: VardaApiService;
  let httpService: HttpService;
  let vardaVakajarjestajaService: VardaVakajarjestajaService;
  let mockVakaJarjestajat;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        AuthService,
        CookieService,
        VardaVakajarjestajaService,
        {provide: Router, useValue: {events: { subscribe: () => {}}, navigate: () => {}}},
        {
          provide: VardaApiService,
          useValue: {
            logout() {},
            checkApiKey() {
              return { subscribe: () => {} };
            }
          }
        },
        {
          provide: HttpService,
          useValue: {}
        }
        ]
    });

    vardaAuthService = TestBed.inject<AuthService>(AuthService);
    vardaApiService = TestBed.inject<VardaApiService>(VardaApiService);
    httpService = TestBed.inject<HttpService>(HttpService);
    vardaVakajarjestajaService = TestBed.inject<VardaVakajarjestajaService>(VardaVakajarjestajaService);
    mockVakaJarjestajat = vakajarjestajatStub;
    vardaVakajarjestajaService.setVakajarjestajat(mockVakaJarjestajat);
  });


  it('Should emit value to asiointikieli subscribers', () => {
    vardaAuthService.loggedInUserAsiointikieliSet().subscribe((asiointikieli) => {
      expect(asiointikieli).toEqual('sv');
    });
    vardaAuthService.setUserAsiointikieli('sv');
    expect(vardaAuthService.loggedInUserAsiointikieli).toEqual('sv');
  });

  it('Should set loggedInUserVakajarjestajaLevelKayttooikeudet if vakajarjestaja found in loggedInUserKayttooikeudet', () => {
    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[0]);
    vardaAuthService.loggedInUserKayttooikeudet = [{'organisaatio': '1.2.246.562.10.67019405222', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA},
    {'organisaatio': '1.2.246.562.10.67019405123', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA}];
    vardaAuthService.initKayttooikeudet();
    expect(vardaAuthService.loggedInUserCurrentKayttooikeus).toEqual(VardaKayttooikeusRoles.VARDA_TALLENTAJA);
    expect(vardaAuthService.loggedInUserVakajarjestajaLevelKayttooikeudet.length).toEqual(1);
    expect(vardaAuthService.loggedInUserToimipaikkaLevelKayttooikeudet.length).toEqual(1);
    expect(vardaAuthService.selectedOrganisationLevelKayttooikeusRole).toEqual(VardaKayttooikeusRoles.VARDA_TALLENTAJA);
  });

  it('Should set loggedInUserToimipaikkaLevelKayttooikeudet if vakajarjestaja not found in loggedInUserKayttooikeudet', () => {
    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[0]);
    vardaAuthService.loggedInUserKayttooikeudet = [{'organisaatio': '1.2.246.562.10.670194052231232', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA},
    {'organisaatio': '1.2.246.562.10.67019405432', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA},
    {'organisaatio': '1.2.246.562.10.67019405123', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA}];
    vardaAuthService.initKayttooikeudet();
    expect(vardaAuthService.loggedInUserCurrentKayttooikeus).toEqual(VardaKayttooikeusRoles.VARDA_KATSELIJA);
    expect(vardaAuthService.loggedInUserVakajarjestajaLevelKayttooikeudet.length).toEqual(0);
    expect(vardaAuthService.loggedInUserToimipaikkaLevelKayttooikeudet.length).toEqual(3);
    expect(vardaAuthService.selectedOrganisationLevelKayttooikeusRole).toEqual(VardaKayttooikeusRoles.VARDA_KATSELIJA);
  });

  it('Should set loggedInUserCurrentKayttooikeus to tallentaja if loggedInUserToimipaikkaLevelKayttooikeudet has tallentaja-role', () => {
    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[0]);
    vardaVakajarjestajaService.tallentajaToimipaikat = toimipaikatStub;
    vardaAuthService.loggedInUserKayttooikeudet = [{'organisaatio': '123123', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA},
    {'organisaatio': '1.2.246.562.10.67019405224', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA}];
    vardaAuthService.initKayttooikeudet();
    expect(vardaAuthService.loggedInUserCurrentKayttooikeus).toEqual(VardaKayttooikeusRoles.VARDA_TALLENTAJA);
    expect(vardaAuthService.loggedInUserToimipaikkaLevelKayttooikeudet.length).toEqual(2);
  });

  it('Should set kayttooikeusRoles correctly when there is only one vakajarjestaja-level permission', () => {
    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[0]);
    vardaAuthService.loggedInUserKayttooikeudet = [{'organisaatio': '1.2.246.562.10.67019405222', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA}];
    vardaAuthService.initKayttooikeudet();
    expect(vardaAuthService.loggedInUserCurrentKayttooikeus).toEqual(VardaKayttooikeusRoles.VARDA_TALLENTAJA);

    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[1]);
    vardaAuthService.loggedInUserKayttooikeudet = [{'organisaatio': '1.2.246.562.10.67019405611', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA}];
    vardaAuthService.initKayttooikeudet();
    expect(vardaAuthService.loggedInUserCurrentKayttooikeus).toEqual(VardaKayttooikeusRoles.VARDA_KATSELIJA);

    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[1]);
    vardaAuthService.loggedInUserKayttooikeudet = [{'organisaatio': '1.2.246.562.10.67019405611', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA}];
    vardaAuthService.initKayttooikeudet();
    expect(vardaAuthService.loggedInUserCurrentKayttooikeus).toEqual(VardaKayttooikeusRoles.VARDA_KATSELIJA);
  });

  it('Should set kayttooikeusRoles correctly when there are both vakajarjestaja and toimipaikka-level permissions', () => {
    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[0]);
    vardaAuthService.loggedInUserKayttooikeudet = [
      {'organisaatio': '1.2.246.562.10.67019405222', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA},
      {'organisaatio': '1.2.246.562.10.670194052231232', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA},
      {'organisaatio': '1.2.246.562.10.670194052231234', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA},
      {'organisaatio': '1.2.246.562.10.670194052231235', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA}];
    vardaAuthService.initKayttooikeudet();
    expect(vardaAuthService.loggedInUserCurrentKayttooikeus).toEqual(VardaKayttooikeusRoles.VARDA_TALLENTAJA);

    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[1]);
    vardaAuthService.loggedInUserKayttooikeudet = [
      {'organisaatio': '1.2.246.562.10.67019405611', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA},
      {'organisaatio': '1.2.246.562.10.670194052231233', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA},
      {'organisaatio': '1.2.246.562.10.670194052231234', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA},
      {'organisaatio': '1.2.246.562.10.670194052231235', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA}];
    vardaAuthService.initKayttooikeudet();
    expect(vardaAuthService.loggedInUserCurrentKayttooikeus).toEqual(VardaKayttooikeusRoles.VARDA_KATSELIJA);
    expect(vardaAuthService.selectedOrganisationLevelKayttooikeusRole).toEqual(VardaKayttooikeusRoles.VARDA_KATSELIJA);
    expect(vardaAuthService.hasToimipaikkaLevelTallentajaRole).toBeFalsy();
  });

  it(`Should set kayttooikeusRoles correctly when there are both
  vakajarjestaja and toimipaikka-level permissions and no tallentaja-roles`, () => {
    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[1]);
    vardaAuthService.loggedInUserKayttooikeudet = [{'organisaatio': '1.2.246.562.10.67019405611', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA},
    {'organisaatio': '1.2.246.562.10.670194052231233', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA},
    {'organisaatio': '1.2.246.562.10.670194052231235', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA}];
    vardaAuthService.initKayttooikeudet();
    expect(vardaAuthService.loggedInUserCurrentKayttooikeus).toEqual(VardaKayttooikeusRoles.VARDA_KATSELIJA);
    expect(vardaAuthService.selectedOrganisationLevelKayttooikeusRole).toEqual(VardaKayttooikeusRoles.VARDA_KATSELIJA);
    expect(vardaAuthService.hasToimipaikkaLevelTallentajaRole).toBeFalsy();
  });

  it(`Should set selectedOrganisationLevelKayttooikeusRole to according to selected vakajarjestaja even if
  loggedInUser has multiple permissions to different vakajarjestajat`, () => {
    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[0]);
    vardaAuthService.loggedInUserKayttooikeudet = [
      {'organisaatio': '1.2.246.562.10.67019405611', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA},
      {'organisaatio': '1.2.246.562.10.67019405222', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA}
    ];
    vardaAuthService.initKayttooikeudet();
    expect(vardaAuthService.loggedInUserCurrentKayttooikeus).toEqual(VardaKayttooikeusRoles.VARDA_TALLENTAJA);
  });

  it(`Should filter out toimipaikat that user has atleast katselija-role to`, () => {
    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[0]);
    vardaAuthService.loggedInUserKayttooikeudet = [
      {'organisaatio': '123123', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA},
      {'organisaatio': '98765346777', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA},
      {'organisaatio': '1.2.246.562.10.67019405222', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA}
    ];
    vardaAuthService.initKayttooikeudet();

    const toimipaikat = vardaAuthService.getAuthorizedToimipaikat(toimipaikatStub);
    expect(vardaAuthService.loggedInUserCurrentKayttooikeus).toEqual(VardaKayttooikeusRoles.VARDA_KATSELIJA);
    expect(vardaAuthService.selectedOrganisationLevelKayttooikeusRole).toEqual(VardaKayttooikeusRoles.VARDA_KATSELIJA);
    expect(vardaAuthService.hasToimipaikkaLevelTallentajaRole).toBeUndefined();
    expect(toimipaikat.length).toEqual(4);
    expect(toimipaikat[0].nimi).toEqual('Espoo');
    expect(toimipaikat[1].nimi).toEqual('Toimipaikka5');
    expect(toimipaikat[2].nimi).toEqual('Kivelän päiväkoti');
    expect(toimipaikat[3].nimi).toEqual('1111aggdgf554saf');
  });

  it(`Should deny access to Etusivu from toimipaikka-level Varda-Tallentaja
  if toimipaikka does not belong to selected vakajarjestaja`, () => {
    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[0]);
    vardaVakajarjestajaService.tallentajaToimipaikat = toimipaikatStub;
    vardaAuthService.loggedInUserKayttooikeudet = [
      {'organisaatio': '9876x5346777', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA},
      {'organisaatio': '1.2.246.562.10.67019405611', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA},
      {'organisaatio': '1.2.246.562.10.67019405222', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA}
    ];
    vardaAuthService.initKayttooikeudet();
    const rv = (vardaAuthService as any).kayttooikeudetHasToimipaikkaLevelTallentajaRole();
    expect(rv).toBeFalsy();
  });

});
