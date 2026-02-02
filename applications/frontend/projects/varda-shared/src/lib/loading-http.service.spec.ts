import { TestBed } from '@angular/core/testing';

import { LoadingHttpService } from './loading-http.service';
import {HttpClient} from '@angular/common/http';

describe('LoadingHttpService', () => {
  beforeEach(() => TestBed.configureTestingModule({
    providers: [
      {provide: HttpClient, useValue: {}}
    ]
  }));

  it('should be created', () => {
    const service: LoadingHttpService = TestBed.inject<LoadingHttpService>(LoadingHttpService);
    expect(service).toBeTruthy();
  });
});
