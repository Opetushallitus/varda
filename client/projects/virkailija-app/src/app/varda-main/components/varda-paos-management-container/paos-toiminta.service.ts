import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaApiService } from '../../../core/services/varda-vakajarjestaja-api.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';

export enum PaosCreateEvent {
  Toimipaikka,
  Toimija,
}

export class OrganisaatioIdentity {
  type: PaosCreateEvent;
  id: number;
}

@Injectable({
  providedIn: 'root'
})
export class PaosToimintaService {
  createEventsSource = new Subject<PaosCreateEvent>();
  // Contains vakajarjestaja and toimipaikka urls
  readonly _createdPaosToimintaOrganisaatioUrl: Array<string>;
  readonly _allToimintaOrganisaatioOidsSource = new Subject<OrganisaatioIdentity>();
  readonly _toimintaDeletedOrganisaatioIdSource = new Subject<OrganisaatioIdentity>();
  readonly errorMessageSource = new Subject<string>();

  i18n = VirkailijaTranslations;

  createEvents$ = this.createEventsSource.asObservable();
  toimintaOrganisaatioId$ = this._allToimintaOrganisaatioOidsSource.asObservable();
  toimintaDeletedOrganisaatioId$ = this._toimintaDeletedOrganisaatioIdSource.asObservable();

  errorMessage$ = this.errorMessageSource.asObservable();

  get createdPaosToimintaOrganisaatioUrl() {
    return [...this._createdPaosToimintaOrganisaatioUrl];
  }

  constructor(
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private vakajarjestajaService: VardaVakajarjestajaService
  ) {
    this._createdPaosToimintaOrganisaatioUrl = [];
  }

  // url can be vakajarjestaja or (paos) toimipaikka url.
  pushCreateEvent(paosCreateEvent: PaosCreateEvent, url: string) {
    this._createdPaosToimintaOrganisaatioUrl.push(url);
    this.createEventsSource.next(paosCreateEvent);
    this.updateToimipaikkalist();
  }

  pushToimintaOrganisaatio(organisaatioId: number, type: PaosCreateEvent) {
    this._allToimintaOrganisaatioOidsSource.next({ id: organisaatioId, type });
  }

  pushDeletedToimintaOrganisaatio(organisaatioId: number, type: PaosCreateEvent) {
    this._toimintaDeletedOrganisaatioIdSource.next({ id: organisaatioId, type });
  }

  updateToimipaikkalist() {
    this.vakajarjestajaApiService.getToimipaikat(this.vakajarjestajaService.getSelectedVakajarjestaja().id).subscribe(
      toimipaikat => this.vakajarjestajaService.setToimipaikat(toimipaikat)
    );
  }

  pushGenericErrorMessage = (err) => {
    console.error(err);
    this.pushErrorMessage(this.i18n.paos_error_generic);
  };

  private pushErrorMessage(errorKey: string) {
    this.errorMessageSource.next(errorKey);
  }
}
