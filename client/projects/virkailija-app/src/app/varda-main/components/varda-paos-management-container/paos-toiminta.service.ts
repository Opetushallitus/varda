import { Injectable } from '@angular/core';
import {Observable, Subject} from 'rxjs';
import {finalize} from 'rxjs/operators';

export enum PaosCreateEvent {
  Toimipaikka,
  Toimija,
}

export class OrganisaatioIdentity {
  type: PaosCreateEvent;
  id: string;
}

@Injectable({
  providedIn: 'root'
})
export class PaosToimintaService {
  private createEventsSource = new Subject<PaosCreateEvent>();
  // Contains vakajarjestaja and toimipaikka urls
  private readonly _createdPaosToimintaOrganisaatioUrl: Array<string>;
  private readonly _allToimintaOrganisaatioOidsSource = new Subject<OrganisaatioIdentity>();
  private readonly _toimintaDeletedOrganisaatioIdSource = new Subject<OrganisaatioIdentity>();
  private readonly errorMessageSource = new Subject<string>();

  createEvents$ = this.createEventsSource.asObservable();
  toimintaOrganisaatioId$ = this._allToimintaOrganisaatioOidsSource.asObservable();
  toimintaDeletedOrganisaatioId$ = this._toimintaDeletedOrganisaatioIdSource.asObservable();

  errorMessage$ = this.errorMessageSource.asObservable();

  get createdPaosToimintaOrganisaatioUrl() {
    return [...this._createdPaosToimintaOrganisaatioUrl];
  }

  constructor() {
    this._createdPaosToimintaOrganisaatioUrl = [];
  }

  // url can be vakajarjestaja or (paos) toimipaikka url.
  pushCreateEvent(paosCreateEvent: PaosCreateEvent, url: string) {
    this._createdPaosToimintaOrganisaatioUrl.push(url);
    this.createEventsSource.next(paosCreateEvent);
  }

  pushToimintaOrganisaatio(organisaatioId: string, type: PaosCreateEvent) {
    this._allToimintaOrganisaatioOidsSource.next({id: organisaatioId, type: type});
  }

  pushDeletedToimintaOrganisaatio(organisaatioId: string, type: PaosCreateEvent) {
    this._toimintaDeletedOrganisaatioIdSource.next({id: organisaatioId, type});
  }

  pushGenericErrorMessage = (err) => {
    console.error(err);
    this.pushErrorMessage('label.paos-management.generic-error');
  }

  private pushErrorMessage(errorKey: string) {
    this.errorMessageSource.next(errorKey);
  }
}
