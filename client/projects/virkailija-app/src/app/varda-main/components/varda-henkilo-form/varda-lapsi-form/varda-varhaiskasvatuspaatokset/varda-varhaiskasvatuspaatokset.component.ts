import { Component, Input, OnInit, QueryList, ViewChildren } from '@angular/core';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaVarhaiskasvatuspaatosComponent } from './varda-varhaiskasvatuspaatos/varda-varhaiskasvatuspaatos.component';
import { VardaFormListAbstractComponent } from '../../varda-form-list-abstract.component';
import { LapsiKoosteVakapaatos } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaVakajarjestajaService } from '../../../../../core/services/varda-vakajarjestaja.service';
import { VardaUtilityService } from '../../../../../core/services/varda-utility.service';
import { ModelNameEnum } from '../../../../../utilities/models/enums/model-name.enum';

@Component({
  selector: 'app-varda-varhaiskasvatuspaatokset',
  templateUrl: './varda-varhaiskasvatuspaatokset.component.html',
  styleUrls: [
    './varda-varhaiskasvatuspaatokset.component.css',
    '../varda-lapsi-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaVarhaiskasvatuspaatoksetComponent extends VardaFormListAbstractComponent<LapsiKoosteVakapaatos> implements OnInit {
  @ViewChildren(VardaVarhaiskasvatuspaatosComponent) objectElements: QueryList<VardaVarhaiskasvatuspaatosComponent>;
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;

  lapsitiedotTallentaja: boolean;
  modelName = ModelNameEnum.VARHAISKASVATUSPAATOS;

  constructor(
    private lapsiService: VardaLapsiService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    utilityService: VardaUtilityService
  ) {
    super(utilityService);
  }

  ngOnInit() {
    super.ngOnInit();
    const activeLapsi = this.lapsiService.activeLapsi.getValue();
    this.objectList = activeLapsi.varhaiskasvatuspaatokset;
    this.lapsitiedotTallentaja = this.toimipaikkaAccess.lapsitiedot.tallentaja;

    const selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    if (activeLapsi.paos_organisaatio_oid && activeLapsi.tallentaja_organisaatio_oid !== selectedVakajarjestaja.organisaatio_oid) {
      this.lapsitiedotTallentaja = false;
    }

    this.addObjectBoolean = this.objectList.length === 0;
  }

  updateActiveObject() {
    const activeLapsi = this.lapsiService.activeLapsi.getValue();
    this.lapsiService.activeLapsi.next({...activeLapsi, varhaiskasvatuspaatokset: this.objectList});
  }
}
