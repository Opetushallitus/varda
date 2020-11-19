import { Injectable } from '@angular/core';
import { VardaVakajarjestajaUi } from '../../utilities/models';
import { BehaviorSubject, Observable } from 'rxjs';
import { VardaToimipaikkaMinimalDto } from '../../utilities/models/dto/varda-toimipaikka-dto.model';
import { FilteredToimipaikat } from '../../utilities/models/varda-filtered-toimipaikat.model';
import { VardaCookieEnum } from '../../utilities/models/enums/varda-cookie.enum';

@Injectable()
export class VardaVakajarjestajaService {

  private vakaJarjestajat$ = new BehaviorSubject<Array<VardaVakajarjestajaUi>>(null);
  private selectedVakajarjestaja: VardaVakajarjestajaUi;
  private selectedVakajarjestaja$ = new BehaviorSubject<VardaVakajarjestajaUi>(null);
  private toimipaikat$ = new BehaviorSubject<Array<VardaToimipaikkaMinimalDto>>(null);
  private filteredToimipaikat: FilteredToimipaikat;

  constructor() { }

  getVakajarjestajat(): Observable<Array<VardaVakajarjestajaUi>> {
    return this.vakaJarjestajat$.asObservable();
  }

  setVakajarjestajat(userVakaJarjestajat: Array<VardaVakajarjestajaUi>): void {
    this.vakaJarjestajat$.next(userVakaJarjestajat);

    const storageVakajarjestaOID = localStorage.getItem(VardaCookieEnum.previous_vakajarjestaja);
    const selectedVakajarjestaja = userVakaJarjestajat.find(vakajarjestaja => vakajarjestaja.organisaatio_oid === storageVakajarjestaOID) || userVakaJarjestajat[0];

    this.setSelectedVakajarjestaja(selectedVakajarjestaja);
  }

  getSelectedVakajarjestaja(): VardaVakajarjestajaUi {
    return { ...this.selectedVakajarjestaja };
  }

  listenSelectedVakajarjestaja(): Observable<VardaVakajarjestajaUi> {
    return this.selectedVakajarjestaja$.asObservable();
  }

  setSelectedVakajarjestaja(vakajarjestaja: VardaVakajarjestajaUi): void {
    this.selectedVakajarjestaja = vakajarjestaja;
    localStorage.setItem(VardaCookieEnum.previous_vakajarjestaja, vakajarjestaja.organisaatio_oid);
    this.selectedVakajarjestaja$.next(vakajarjestaja);
  }

  /**
   * fetches ALL toimipaikat user can see
   * prefiltered toimipaikat can be called with
   * @remarks eg. vakajarjestajaService.getFilteredToimipaikat()
  */
  getToimipaikat() {
    return this.toimipaikat$.asObservable();
  }

  setToimipaikat(toimipaikat: Array<VardaToimipaikkaMinimalDto>) {
    this.toimipaikat$.next(toimipaikat);
  }

  /** to avoid cyclic dependency this is set by authService after getting toimipaikat */
  setFilteredToimipaikat(filteredToimipaikat: FilteredToimipaikat) {
    this.filteredToimipaikat = filteredToimipaikat;
  }

  /**
   * fetches prefiltered toimipaikat user can see
   * @remarks for more detailed filtering use eg. authService.getAuthorizedToimipaikat(toimipaikat, SaveAccess)
  */
  getFilteredToimipaikat(): FilteredToimipaikat {
    return { ...this.filteredToimipaikat };
  }
}
