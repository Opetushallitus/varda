import { Injectable } from '@angular/core';
import { LoadingHttpService } from 'varda-shared';
import { Observable, Subject } from 'rxjs';


@Injectable()
export class VardaLapsiService {
  private updateLapsiList$ = new Subject();

  constructor(private http: LoadingHttpService) { }


  // listeners
  listenLapsiListUpdate(): Observable<any> {
    return this.updateLapsiList$.asObservable();
  }

  sendLapsiListUpdate() {
    this.updateLapsiList$.next(true);
  }

}
