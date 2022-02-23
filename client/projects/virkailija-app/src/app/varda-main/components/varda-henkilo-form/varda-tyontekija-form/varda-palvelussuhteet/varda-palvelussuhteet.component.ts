import { Component, OnInit, Input, ViewChildren, QueryList } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaPalvelussuhdeDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-palvelussuhde-dto.model';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { VardaPalvelussuhdeComponent } from './varda-palvelussuhde/varda-palvelussuhde.component';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaFormListAbstractComponent } from '../../varda-form-list-abstract.component';

@Component({
  selector: 'app-varda-palvelussuhteet',
  templateUrl: './varda-palvelussuhteet.component.html',
  styleUrls: [
    './varda-palvelussuhteet.component.css',
    '../varda-tyontekija-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaPalvelussuhteetComponent extends VardaFormListAbstractComponent implements OnInit {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() tyontekija: TyontekijaListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() henkilonTutkinnot: Array<VardaTutkintoDTO>;
  @ViewChildren(VardaPalvelussuhdeComponent) objectElements: QueryList<VardaPalvelussuhdeComponent>;
  palvelussuhteet: Array<VardaPalvelussuhdeDTO>;

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private snackBarService: VardaSnackBarService,
  ) {
    super();
  }

  ngOnInit() {
    if (this.toimipaikkaAccess.tyontekijatiedot.katselija) {
      this.getObjects();
    } else {
      this.palvelussuhteet = [];
    }
  }

  getObjects() {
    this.palvelussuhteet = null;

    this.henkilostoService.getPalvelussuhteet(this.tyontekija.id).subscribe({
      next: palvelussuhdeData => {
        this.palvelussuhteet = palvelussuhdeData;
      },
      error: err => this.snackBarService.errorWithConsole(this.i18n.palvelussuhteet_fetch_failure, err)
    });
  }
}
