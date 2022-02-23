import { Component, OnInit, Input, ViewChildren, QueryList } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { VardaPoissaoloDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-poissolo-dto.model';
import { VardaTyontekijaTaydennyskoulutusComponent } from './varda-tyontekija-taydennyskoulutus/varda-tyontekija-taydennyskoulutus.component';
import { KoodistoDTO, KoodistoEnum } from 'projects/varda-shared/src/lib/models/koodisto-models';
import { VardaKoodistoService } from 'varda-shared';
import { forkJoin } from 'rxjs';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaFormListAbstractComponent } from '../../varda-form-list-abstract.component';

@Component({
  selector: 'app-varda-tyontekija-taydennyskoulutukset',
  templateUrl: './varda-tyontekija-taydennyskoulutukset.component.html',
  styleUrls: [
    './varda-tyontekija-taydennyskoulutukset.component.css',
    '../varda-tyontekija-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaTyontekijaTaydennyskoulutuksetComponent extends VardaFormListAbstractComponent implements OnInit {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() tyontekija: TyontekijaListDTO;
  @ViewChildren(VardaTyontekijaTaydennyskoulutusComponent) objectElements: QueryList<VardaTyontekijaTaydennyskoulutusComponent>;
  taydennyskoulutukset: Array<VardaPoissaoloDTO>;
  tehtavanimikkeet: KoodistoDTO;

  constructor(
    private koodistoService: VardaKoodistoService,
    private henkilostoService: VardaHenkilostoApiService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private snackBarService: VardaSnackBarService,
  ) {
    super();
  }

  ngOnInit() {
    if (this.toimipaikkaAccess.taydennyskoulutustiedot.katselija) {
      this.getObjects();
      this.setTehtavanimikkeet();
    } else {
      this.taydennyskoulutukset = [];
    }

    this.expandPanel = this.toimipaikkaAccess.taydennyskoulutustiedot.katselija && !this.toimipaikkaAccess.tyontekijatiedot.katselija;
  }

  setTehtavanimikkeet() {
    const searchParams = { vakajarjestaja_oid: this.vakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid, henkilo_oid: this.tyontekija.henkilo_oid };
    forkJoin([
      this.koodistoService.getKoodisto(KoodistoEnum.tehtavanimike),
      this.henkilostoService.getTaydennyskoulutuksetTyontekijat(searchParams)
    ]).subscribe(([koodisto, henkiloNimikkeet]) => {
      henkiloNimikkeet = henkiloNimikkeet.filter(henkilo => henkilo.henkilo_oid === this.tyontekija.henkilo_oid);
      this.tehtavanimikkeet = koodisto;
      this.tehtavanimikkeet.codes = koodisto.codes.filter(code => henkiloNimikkeet.find(henkilo => henkilo.tehtavanimike_koodit?.includes(code.code_value)));
    });
  }

  getObjects() {
    this.taydennyskoulutukset = null;
    const searchParams = { tyontekija: this.tyontekija.id };
    this.henkilostoService.getTaydennyskoulutukset(searchParams).subscribe({
      next: taydennyskoulutusData => {
        this.taydennyskoulutukset = taydennyskoulutusData;
      },
      error: err => this.snackBarService.errorWithConsole(this.i18n.taydennyskoulutukset_fetch_failure, err)
    });
  }

  initObject() {
    super.initObject();
    this.setTehtavanimikkeet();
  }

  closeObject(refreshObjects?: boolean, hideAddObject?: boolean) {
    super.closeObject(refreshObjects, hideAddObject);
    if (refreshObjects) {
      this.setTehtavanimikkeet();
    }
  }
}
