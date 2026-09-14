import { Component, Input, OnInit, QueryList, ViewChildren } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaTyontekijaTaydennyskoulutusComponent } from './varda-tyontekija-taydennyskoulutus/varda-tyontekija-taydennyskoulutus.component';
import { CodeDTO, KoodistoEnum, KoodistoSortBy, VardaKoodistoService } from 'varda-shared';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaFormListAbstractComponent } from '../../varda-form-list-abstract.component';
import { TyontekijaTaydennyskoulutus } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { sortByName, sortBySuoritusPvm } from '../../../../../utilities/helper-functions';
import { switchMap } from 'rxjs/operators';
import { VardaUtilityService } from '../../../../../core/services/varda-utility.service';
import { ModelNameEnum } from '../../../../../utilities/models/enums/model-name.enum';

@Component({
    selector: 'app-varda-tyontekija-taydennyskoulutukset',
    templateUrl: './varda-tyontekija-taydennyskoulutukset.component.html',
    styleUrls: [
        './varda-tyontekija-taydennyskoulutukset.component.css',
        '../varda-tyontekija-form.component.css',
        '../../varda-henkilo-form.component.css'
    ],
    standalone: false
})
export class VardaTyontekijaTaydennyskoulutuksetComponent
  extends VardaFormListAbstractComponent<TyontekijaTaydennyskoulutus>
  implements OnInit {
  @ViewChildren(VardaTyontekijaTaydennyskoulutusComponent) objectElements: QueryList<VardaTyontekijaTaydennyskoulutusComponent>;
  @Input() toimipaikkaAccess: UserAccess;

  tehtavanimikeCodes: Array<CodeDTO> = [];
  tehtavanimikeOptions: Array<CodeDTO> = [];
  tehtavanimikeList: Array<string> = [];
  modelName = ModelNameEnum.TAYDENNYSKOULUTUS;

  sortByFunction = sortBySuoritusPvm;

  constructor(
    private koodistoService: VardaKoodistoService,
    private henkilostoService: VardaHenkilostoApiService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private snackBarService: VardaSnackBarService,
    utilityService: VardaUtilityService
  ) {
    super(utilityService);
  }

  ngOnInit() {
    super.ngOnInit();
    this.objectList = this.henkilostoService.activeTyontekija.getValue().taydennyskoulutukset.sort(sortBySuoritusPvm);

    const selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    const henkiloOid = this.henkilostoService.activeTyontekija.getValue().henkilo.henkilo_oid;

    this.subscriptions.push(
      this.koodistoService.getKoodisto(KoodistoEnum.tehtavanimike, KoodistoSortBy.name).subscribe(result => {
        this.tehtavanimikeCodes = result.codes;
        this.updateTehtavanimikeOptions();
      }),
      this.henkilostoService.tyoskentelypaikkaChanged.pipe(
        switchMap(() => this.henkilostoService.getTaydennyskoulutuksetTyontekijat({
          vakajarjestaja_oid: selectedVakajarjestaja.organisaatio_oid,
          henkilo_oid: henkiloOid
        }))
      ).subscribe({
        next: result => {
          if (result.length === 1 && result[0].henkilo_oid === henkiloOid) {
            this.tehtavanimikeList = result[0].tehtavanimike_koodit;
          } else {
            this.tehtavanimikeList = [];
          }
          this.updateTehtavanimikeOptions();
        },
        error: err => this.snackBarService.errorWithConsole(this.i18n.taydennyskoulutukset_fetch_failure, err)
      })
    );

    this.expandPanel = this.toimipaikkaAccess.taydennyskoulutustiedot.katselija && !this.toimipaikkaAccess.tyontekijatiedot.katselija;
  }

  updateTehtavanimikeOptions() {
    this.tehtavanimikeOptions = this.tehtavanimikeCodes.filter(code => this.tehtavanimikeList.some(
      tehtavanimike => tehtavanimike.toLowerCase() === code.code_value.toLowerCase()
    )).sort(sortByName);
  }

  updateActiveObject() {
    const activeTyontekija = this.henkilostoService.activeTyontekija.getValue();
    this.henkilostoService.activeTyontekija.next({...activeTyontekija, taydennyskoulutukset: this.objectList});
  }
}
