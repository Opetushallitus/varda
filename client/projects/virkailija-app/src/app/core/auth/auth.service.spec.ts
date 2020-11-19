/*
palauta @ https://jira.eduuni.fi/browse/CSCVARDA-2080
import { TestBed } from '@angular/core/testing';
import { AuthService } from './auth.service';
import { VardaApiService } from '../services/varda-api.service';
import { CookieService } from 'ngx-cookie-service';
import { Router } from '@angular/router';
import { vakajarjestajatStub } from '../../shared/testmocks/vakajarjestajat-stub';
import { VardaVakajarjestajaService } from '../services/varda-vakajarjestaja.service';
import { toimipaikatStub } from '../../shared/testmocks/toimipaikat-stub';
import { VardaKayttooikeusRoles } from '../../utilities/varda-kayttooikeus-roles';
import { HttpService } from 'varda-shared';
import { VardaToimipaikkaDTO, VardaVakajarjestaja } from '../../utilities/models';
import { SaveAccess } from '../../utilities/models/varda-user-access.model';
import { VardaToimipaikkaMinimalDto } from '../../utilities/models/dto/varda-toimipaikka-dto.model';
import { EMPTY } from 'rxjs';
import { toimipaikatMinStub } from '../../shared/testmocks/toimipaikat-min-stub';

describe('AuthService', () => {

  let vardaAuthService: AuthService;
  let vardaApiService: VardaApiService;
  let httpService: HttpService;
  let vardaVakajarjestajaService: VardaVakajarjestajaService;
  let mockVakaJarjestajat: Array<VardaVakajarjestaja>;
  let mockMinToimipaikat: Array<VardaToimipaikkaMinimalDto>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        AuthService,
        CookieService,
        VardaVakajarjestajaService,
        { provide: Router, useValue: { events: EMPTY, navigate: () => { }, url: '/haku' } },
        {
          provide: VardaApiService,
          useValue: {
            logout() { },
            checkApiKey() {
              return { subscribe: () => { } };
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
    mockMinToimipaikat = toimipaikatMinStub;
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
    vardaAuthService.loggedInUserKayttooikeudet = [
      { 'organisaatio': '98765346777', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA },
      { 'organisaatio': '1.2.246.562.10.67019405222', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA },
      { 'organisaatio': '1.2.246.562.10.67019405123', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA }];
    vardaAuthService.initUserAccess(mockMinToimipaikat);
    expect(vardaAuthService.loggedInUserVakajarjestajaLevelKayttooikeudet.length).toEqual(1);
    expect(vardaAuthService.loggedInUserToimipaikkaLevelKayttooikeudet.length).toEqual(1);

    vardaAuthService.toimipaikkaAccessToAnyToimipaikka$.subscribe(toimipaikkaAccessToAny =>
      expect(toimipaikkaAccessToAny.lapsitiedot.tallentaja).toEqual(true)
    );
  });

  it('Should set loggedInUserToimipaikkaLevelKayttooikeudet if vakajarjestaja not found in loggedInUserKayttooikeudet', () => {
    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[0]);
    vardaAuthService.loggedInUserKayttooikeudet = [
      { 'organisaatio': '98765346777', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA }
    ];
    vardaAuthService.initUserAccess(mockMinToimipaikat);
    expect(vardaAuthService.loggedInUserVakajarjestajaLevelKayttooikeudet.length).toEqual(0);
    expect(vardaAuthService.loggedInUserToimipaikkaLevelKayttooikeudet.length).toEqual(1);

    vardaAuthService.toimipaikkaAccessToAnyToimipaikka$.subscribe(toimipaikkaAccessToAny =>
      expect(toimipaikkaAccessToAny.lapsitiedot.tallentaja).toEqual(true)
    );

    const toimijaAccess = vardaAuthService.getUserAccess();
    expect(toimijaAccess.lapsitiedot.tallentaja).toBeFalse();
  });

  it(`Should filter out toimipaikat that user has atleast katselija-role to`, () => {
    vardaVakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatStub[0]);
    vardaAuthService.loggedInUserKayttooikeudet = [
      { 'organisaatio': '123123', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA },
      { 'organisaatio': '98765346777', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_TALLENTAJA },
      { 'organisaatio': '1.2.246.562.10.67019405222', 'kayttooikeus': VardaKayttooikeusRoles.VARDA_KATSELIJA }
    ];
    vardaAuthService.initUserAccess(mockMinToimipaikat);

    const toimipaikat = vardaAuthService.getAuthorizedToimipaikat(mockMinToimipaikat, SaveAccess.lapsitiedot);
    expect(toimipaikat.length).toEqual(1);
    expect(toimipaikat[0].nimi).toEqual('Kivelän päiväkoti');
  });
});
 */
