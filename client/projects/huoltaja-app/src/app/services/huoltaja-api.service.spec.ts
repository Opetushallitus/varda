import { TestBed } from '@angular/core/testing';

import { HuoltajaApiService } from './huoltaja-api.service';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

describe('HuoltajaApiService', () => {
  beforeEach(() => TestBed.configureTestingModule({
    providers: [
      { provide: HttpClient, useValue: {} },
      { provide: Router, useValue: {} }
    ]
  }));

  it('should be created', () => {
    const service: HuoltajaApiService = TestBed.inject<HuoltajaApiService>(HuoltajaApiService);
    expect(service).toBeTruthy();
  });
});
