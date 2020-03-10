import { TestBed } from '@angular/core/testing';

import { PaosToimintaService } from './paos-toiminta.service';

describe('PaosToimintaService', () => {
  beforeEach(() => TestBed.configureTestingModule({}));

  it('should be created', () => {
    const service: PaosToimintaService = TestBed.inject<PaosToimintaService>(PaosToimintaService);
    expect(service).toBeTruthy();
  });
});
