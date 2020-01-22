import { TestBed, inject } from '@angular/core/testing';

import { VardaVakajarjestajaService } from './varda-vakajarjestaja.service';

describe('VardaVakajarjestajaService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VardaVakajarjestajaService]
    });
  });

  it('should be created', inject([VardaVakajarjestajaService], (service: VardaVakajarjestajaService) => {
    expect(service).toBeTruthy();
  }));
});
