import { OnInit, Input, Directive } from '@angular/core';
import { VardaVakajarjestaja } from '../../../../utilities/models/varda-vakajarjestaja.model';
import { mergeMap } from 'rxjs/operators';
import { from, Observable, Subject } from 'rxjs';
import { PaosOikeusTieto, PaosToimintatietoDto, PaosToimipaikkatietoDto } from '../../../../utilities/models/dto/varda-paos-dto';

@Directive()
export abstract class AbstractPaosListToimintainfoComponentDirective<T
  extends PaosToimipaikkatietoDto & PaosToimintatietoDto>
  implements OnInit {
  @Input() selectedVakajarjestaja: VardaVakajarjestaja;
  @Input() isVardaPaakayttaja: boolean;
  @Input() isAdminUser: boolean;

  paosToiminnat: Array<T>;
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
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
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
      mergeMap(res => from(res))
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

  getCurrentTallentajaName(paosOikeus: PaosOikeusTieto, organisaatioNimi: string) {
    return (
      paosOikeus.tallentaja_organisaatio_oid === this.selectedVakajarjestaja.organisaatio_oid ?
        this.selectedVakajarjestaja.nimi : organisaatioNimi
    );
  }
}
