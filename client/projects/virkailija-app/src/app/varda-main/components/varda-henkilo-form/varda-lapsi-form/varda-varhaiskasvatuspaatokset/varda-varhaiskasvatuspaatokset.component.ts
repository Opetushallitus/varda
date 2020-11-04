import { Component, OnInit, Input, ViewChildren, QueryList } from '@angular/core';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaPaosApiService } from 'projects/virkailija-app/src/app/core/services/varda-paos-api.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaToimipaikkaDTO, VardaVakajarjestajaUi, VardaVarhaiskasvatuspaatosDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { LapsiListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Observable } from 'rxjs';
import { VardaVarhaiskasvatuspaatosComponent } from './varda-varhaiskasvatuspaatos/varda-varhaiskasvatuspaatos.component';

@Component({
  selector: 'app-varda-varhaiskasvatuspaatokset',
  templateUrl: './varda-varhaiskasvatuspaatokset.component.html',
  styleUrls: [
    './varda-varhaiskasvatuspaatokset.component.css',
    '../varda-lapsi-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaVarhaiskasvatuspaatoksetComponent implements OnInit {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() lapsi: LapsiListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() selectedVakajarjestaja: VardaVakajarjestajaUi;
  @ViewChildren(VardaVarhaiskasvatuspaatosComponent) varhaiskasvatuspaatosElements: QueryList<VardaVarhaiskasvatuspaatosComponent>;
  i18n = VirkailijaTranslations;
  expandPanel = true;
  currentToimipaikka: VardaToimipaikkaDTO;
  varhaiskasvatuspaatokset: Array<VardaVarhaiskasvatuspaatosDTO>;
  addVarhaiskasvatuspaatosBoolean: boolean;
  lapsitiedotTallentaja: boolean;


  constructor(
    private lapsiService: VardaLapsiService,
    private modalService: VardaModalService,
    private snackBarService: VardaSnackBarService,
    private paosService: VardaPaosApiService,
  ) {

  }


  ngOnInit() {
    this.initPaosOikeus(this.toimipaikkaAccess.lapsitiedot.tallentaja).subscribe(tallentaja => {
      this.lapsitiedotTallentaja = tallentaja;

      if (this.toimipaikkaAccess.lapsitiedot.katselija) {
        this.getVarhaiskasvatuspaatokset();
      } else {
        this.varhaiskasvatuspaatokset = [];
      }
    });
  }

  togglePanel(open: boolean) {
    this.expandPanel = open;
  }

  getVarhaiskasvatuspaatokset() {
    this.varhaiskasvatuspaatokset = null;

    this.lapsiService.getVarhaiskasvatuspaatokset(this.lapsi.id).subscribe({
      next: palvelussuhdeData => {
        this.varhaiskasvatuspaatokset = palvelussuhdeData;
        if (this.varhaiskasvatuspaatokset.length === 0 && this.lapsitiedotTallentaja) {
          setTimeout(() => {
            this.initVarhaiskasvatuspaatos();
            this.modalService.setFormValuesChanged(true);
          }, 1000);
        }
      },
      error: err => this.snackBarService.errorWithConsole(this.i18n.varhaiskasvatuspaatokset_fetch_failure, err)
    });
  }

  initVarhaiskasvatuspaatos() {
    this.addVarhaiskasvatuspaatosBoolean = true;
    setTimeout(() => this.togglePanel(true), 0);
    setTimeout(() => this.varhaiskasvatuspaatosElements.last.element.nativeElement.scrollIntoView({ behavior: 'smooth' }), 100);
  }

  closeAddVarhaiskasvatuspaatos(refreshSuhteet?: boolean) {
    this.addVarhaiskasvatuspaatosBoolean = false;
    if (refreshSuhteet) {
      this.getVarhaiskasvatuspaatokset();
    }
  }

  initPaosOikeus(tallentaja: boolean): Observable<boolean> {
    return new Observable(paosObs => {
      if (!this.lapsi.paos_organisaatio_oid) {
        paosObs.next(tallentaja);
        paosObs.complete();
      } else if (this.lapsi.paos_organisaatio_oid === this.selectedVakajarjestaja.organisaatio_oid) {
        paosObs.next(tallentaja);
        paosObs.complete();
      } else {
        this.paosService.getPaosToimipaikat(this.selectedVakajarjestaja.id).subscribe({
          next: paosToimipaikkaData => {
            const paosToimipaikka = paosToimipaikkaData.find(toimipaikka =>
              [this.lapsi.paos_organisaatio_oid, this.lapsi.oma_organisaatio_oid].includes(toimipaikka.toimija_organisaatio_oid)
            );

            if (paosToimipaikka) {
              tallentaja = paosToimipaikka.paos_oikeus.tallentaja_organisaatio_oid === this.selectedVakajarjestaja.organisaatio_oid;
            }
          },
          error: err => {
            console.log(err);
          }
        }).add(() => {
          paosObs.next(tallentaja);
          paosObs.complete();
        });
      }
    });
  }
}
