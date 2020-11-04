import { Component, OnInit, OnChanges, Input, ViewChildren, QueryList } from '@angular/core';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { LapsiListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { VardaMaksutietoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-maksutieto-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { KoodistoDTO } from 'varda-shared';
import { VardaMaksutietoComponent } from './varda-maksutieto/varda-maksutieto.component';


@Component({
  selector: 'app-varda-maksutiedot',
  templateUrl: './varda-maksutiedot.component.html',
  styleUrls: [
    './varda-maksutiedot.component.css',
    '../varda-lapsi-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaMaksutiedotComponent implements OnInit, OnChanges {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() selectedVakajarjestaja: VardaVakajarjestajaUi;
  @Input() lapsi: LapsiListDTO;
  @ViewChildren(VardaMaksutietoComponent) maksutietoElements: QueryList<VardaMaksutietoComponent>;
  i18n = VirkailijaTranslations;
  expandPanel = true;
  maksutiedot: Array<VardaMaksutietoDTO>;
  tehtavanimikkeet: KoodistoDTO;
  addMaksutieto: boolean;
  maksutietoOikeus: boolean;

  constructor(
    private lapsiService: VardaLapsiService,
    private authService: AuthService,
    private snackBarService: VardaSnackBarService,
  ) {

  }

  ngOnInit() {
    this.paosTarkastelu();

    if (this.maksutietoOikeus && this.toimipaikkaAccess.huoltajatiedot.katselija) {
      this.getMaksutiedot();
    } else {
      this.maksutiedot = [];
    }
  }

  ngOnChanges() { }

  togglePanel(open: boolean) {
    this.expandPanel = open;
  }

  getMaksutiedot() {

    this.maksutiedot = null;
    this.lapsiService.getMaksutiedot(this.lapsi.id).subscribe({
      next: taydennyskoulutusData => this.maksutiedot = taydennyskoulutusData,
      error: err => this.snackBarService.errorWithConsole(this.i18n.maksutiedot_fetch_failure, err)
    });
  }

  initMaksutieto() {
    this.addMaksutieto = true;
    setTimeout(() => this.togglePanel(true), 0);
    setTimeout(() => this.maksutietoElements.last.element.nativeElement.scrollIntoView({ behavior: 'smooth' }), 100);
  }

  closeAddMaksutieto(refreshSuhteet?: boolean) {
    this.addMaksutieto = false;
    if (refreshSuhteet) {
      this.getMaksutiedot();
    }
  }

  paosTarkastelu() {
    // enable maksutiedot for non-paos and your own paos-kids
    if (!this.lapsi.oma_organisaatio_oid || this.lapsi.oma_organisaatio_oid === this.selectedVakajarjestaja.organisaatio_oid) {
      this.maksutietoOikeus = true;
    }
  }

}
