import {OnInit, Input} from '@angular/core';
import {VardaVakajarjestaja} from '../../../../utilities/models/varda-vakajarjestaja.model';
import { flatMap } from 'rxjs/operators';
import {from, Observable, Subject} from 'rxjs';
import {PaosOikeusTieto, PaosToimintatietoDto, PaosToimipaikkatietoDto} from '../../../../utilities/models/dto/varda-paos-dto';

export abstract class AbstractPaosListToimintainfoComponent<T extends PaosToimipaikkatietoDto & PaosToimintatietoDto> implements OnInit {
  paosToiminnat: Array<T>;
  @Input() selectedVakajarjestaja: VardaVakajarjestaja;
  showSuccess = false;
  showConfirmModal$ = new Subject<boolean>();
  paosToimintaToDelete: T;

  // Override
  abstract apiServiceMethod: () => Observable<Array<T>>;
  // Override
  abstract pushToimintaOrganisaatioId: (paosToiminta: T) => void;
  // Override optional
  getPaosToiminnatOnCompleteHook() { }
  // Override optional
  getPaosToiminnatErrorHook(err) { }

  ngOnInit(): void {
    this.paosToiminnat = [];
    this.getPaosToiminnat();
  }

  // Show success message and hide it after delay
  showAndHideSuccessMessage() {
    this.showSuccess = true;
    setTimeout(() => {
      this.showSuccess = false;
    }, 2000);
  }

  showDeleteConfirm(paosToiminta: T) {
    this.paosToimintaToDelete = paosToiminta;
    this.showConfirmModal$.next(true);
  }

  getPaosToiminnat() {
    this.paosToiminnat = [];
    return this.apiServiceMethod().pipe(
      flatMap(res => from(res))
    ).subscribe({
      next: paosToiminta => {
        this.paosToiminnat.push(paosToiminta);
        this.pushToimintaOrganisaatioId(paosToiminta);
      },
      error: err => {
        this.getPaosToiminnatErrorHook(err);
      },
      complete: () => {
        this.getPaosToiminnatOnCompleteHook();
      }
    });
  }

  getCurrentTallentajaTranslateKey(paosOikeus: PaosOikeusTieto) {
    return paosOikeus.tallentaja_organisaatio_oid === this.selectedVakajarjestaja.organisaatio_oid ? 'label.tallentaja' : 'label.katselija';
  }

}
