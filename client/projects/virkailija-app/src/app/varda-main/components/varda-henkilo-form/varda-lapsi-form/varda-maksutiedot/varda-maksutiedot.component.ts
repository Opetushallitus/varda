import { Component, OnInit, Input, ViewChildren, QueryList } from '@angular/core';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { LapsiListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { VardaMaksutietoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-maksutieto-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { KoodistoDTO } from 'varda-shared';
import { VardaMaksutietoComponent } from './varda-maksutieto/varda-maksutieto.component';
import { VardaFormListAbstractComponent } from '../../varda-form-list-abstract.component';


@Component({
  selector: 'app-varda-maksutiedot',
  templateUrl: './varda-maksutiedot.component.html',
  styleUrls: [
    './varda-maksutiedot.component.css',
    '../varda-lapsi-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaMaksutiedotComponent extends VardaFormListAbstractComponent implements OnInit {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() selectedVakajarjestaja: VardaVakajarjestajaUi;
  @Input() lapsi: LapsiListDTO;
  @ViewChildren(VardaMaksutietoComponent) objectElements: QueryList<VardaMaksutietoComponent>;
  maksutiedot: Array<VardaMaksutietoDTO>;
  tehtavanimikkeet: KoodistoDTO;
  maksutietoOikeus: boolean;

  constructor(
    private lapsiService: VardaLapsiService,
    private snackBarService: VardaSnackBarService,
  ) {
    super();
  }

  ngOnInit() {
    this.paosTarkastelu();

    if (this.maksutietoOikeus && this.toimipaikkaAccess.huoltajatiedot.katselija) {
      this.getObjects();
    } else {
      this.maksutiedot = [];
    }
  }

  getObjects() {
    this.maksutiedot = null;
    this.lapsiService.getMaksutiedot(this.lapsi.id).subscribe({
      next: taydennyskoulutusData => {
        this.maksutiedot = taydennyskoulutusData;
      },
      error: err => this.snackBarService.errorWithConsole(this.i18n.maksutiedot_fetch_failure, err)
    });
  }

  paosTarkastelu() {
    // enable maksutiedot for non-paos and your own paos-kids
    if (!this.lapsi.oma_organisaatio_oid || this.lapsi.oma_organisaatio_oid === this.selectedVakajarjestaja.organisaatio_oid) {
      this.maksutietoOikeus = true;
    }
  }
}
