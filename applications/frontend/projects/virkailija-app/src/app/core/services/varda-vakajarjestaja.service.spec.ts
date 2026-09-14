import { TestBed } from '@angular/core/testing';
import { toimipaikatMinStub } from '../../shared/testmocks/toimipaikat-min-stub';
import { vakajarjestajatUIStub } from '../../shared/testmocks/vakajarjestajat-stub';
import { VardaCookieEnum } from '../../utilities/models/enums/varda-cookie.enum';
import { VardaVakajarjestajaService } from './varda-vakajarjestaja.service';

describe('VakajarjestajaService', () => {
  let vakajarjestajaService: VardaVakajarjestajaService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        VardaVakajarjestajaService
      ]
    });

    vakajarjestajaService = TestBed.inject<VardaVakajarjestajaService>(VardaVakajarjestajaService);
  });

  it('should set vakajarjestajat', () => {
    localStorage.removeItem(VardaCookieEnum.previous_vakajarjestaja);
    vakajarjestajaService.setVakajarjestajat(vakajarjestajatUIStub);

    vakajarjestajaService.getVakajarjestajat().subscribe(vakajarjestajat => {
      expect(vakajarjestajat.length).toEqual(vakajarjestajatUIStub.length);
      expect(vakajarjestajaService.getSelectedVakajarjestaja()).toEqual(vakajarjestajatUIStub[0]);
    });
  });

  it('should set default vakajarjestaja from cookie', () => {
    localStorage.setItem(VardaCookieEnum.previous_vakajarjestaja, vakajarjestajatUIStub[1].organisaatio_oid);
    vakajarjestajaService.setVakajarjestajat(vakajarjestajatUIStub);

    vakajarjestajaService.getVakajarjestajat().subscribe(vakajarjestajat => {
      expect(vakajarjestajat.length).toEqual(vakajarjestajatUIStub.length);
      expect(vakajarjestajaService.getSelectedVakajarjestaja()).toEqual(vakajarjestajatUIStub[1]);
    });
  });

  it('should change default vakajarjestaja', () => {
    vakajarjestajaService.setVakajarjestajat(vakajarjestajatUIStub);
    vakajarjestajaService.setSelectedVakajarjestaja(vakajarjestajatUIStub[2]);
    expect(vakajarjestajaService.getSelectedVakajarjestaja()).toEqual(vakajarjestajatUIStub[2]);
  });

  it('should set toimipaikat', () => {
    vakajarjestajaService.setToimipaikat(toimipaikatMinStub);

    vakajarjestajaService.getToimipaikat().subscribe(toimipaikat =>
      expect(toimipaikat.length).toEqual(toimipaikatMinStub.length)
    );
  });
});
