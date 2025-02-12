import { TestBed } from '@angular/core/testing';
import { VardaKayttajatyyppi } from 'varda-shared';
import { toimipaikatMinStub } from '../../shared/testmocks/toimipaikat-min-stub';
import { vakajarjestajatUIStub } from '../../shared/testmocks/vakajarjestajat-stub';
import { VardaKayttooikeusRoles } from '../../utilities/models';
import { VardaVakajarjestajaService } from '../services/varda-vakajarjestaja.service';
import { AuthService } from './auth.service';

describe('AuthService', () => {

  let authService: AuthService;
  let vakajarjestajaService: VardaVakajarjestajaService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        AuthService,
        VardaVakajarjestajaService
      ]
    });

    authService = TestBed.inject<AuthService>(AuthService);
    vakajarjestajaService = TestBed.inject<VardaVakajarjestajaService>(VardaVakajarjestajaService);

    vakajarjestajaService.setVakajarjestajat(vakajarjestajatUIStub);
    vakajarjestajaService.setSelectedVakajarjestaja(
      vakajarjestajatUIStub.find(vakaj => vakaj.organisaatio_oid === '1.2.246.562.10.67019405222')
    );
    vakajarjestajaService.setToimipaikat(toimipaikatMinStub);
    const kayttoObs = authService.setPermissions({
      kayttajatyyppi: VardaKayttajatyyppi.VIRKAILIJA,
      kayttooikeudet: [
        { organisaatio: '1.2.246.562.10.67019405611', kayttooikeus: VardaKayttooikeusRoles.HENKILOSTO_TYONTEKIJA_TALLENTAJA },
        { organisaatio: '1.2.246.562.10.67019405222', kayttooikeus: VardaKayttooikeusRoles.VARDA_TALLENTAJA },
        { organisaatio: 'toimipaikka_0005', kayttooikeus: VardaKayttooikeusRoles.HENKILOSTO_VUOKRATTU_KATSELIJA },
        { organisaatio: 'toimipaikka_0004', kayttooikeus: VardaKayttooikeusRoles.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA },
      ]
    });

    kayttoObs.subscribe(() => authService.initUserPermissions(toimipaikatMinStub));
  });

  it('checking toimipaikkaAccessIfAny', () => {
    const toimipaikkaAccessToAny = authService.anyUserAccess;
    expect(toimipaikkaAccessToAny.vuokrattuHenkilosto.katselija).toBeTrue();
    expect(toimipaikkaAccessToAny.vuokrattuHenkilosto.tallentaja).toBeFalse();
    expect(toimipaikkaAccessToAny.lapsitiedot.tallentaja).toBeTrue();
    expect(toimipaikkaAccessToAny.taydennyskoulutustiedot.katselija).toBeFalse();
  });

  it('checking toimijaAccess', () => {
    const toimijaAccess = authService.organisaatioUserAccess;
    expect(toimijaAccess.vuokrattuHenkilosto.katselija).toBeFalse();
    expect(toimijaAccess.lapsitiedot.tallentaja).toBeTrue();
  });

  it('checking toimipaikkaAccess', () => {
    const toimijaAccess = authService.getUserAccess('toimipaikka_0005');
    expect(toimijaAccess.vuokrattuHenkilosto.katselija).toBeTrue();
    expect(toimijaAccess.vuokrattuHenkilosto.tallentaja).toBeFalse();
    expect(toimijaAccess.lapsitiedot.tallentaja).toBeTrue();
  });
});
