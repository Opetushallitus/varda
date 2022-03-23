import { Component, OnInit, Input, ViewChildren, QueryList } from '@angular/core';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaVarhaiskasvatuspaatosComponent } from './varda-varhaiskasvatuspaatos/varda-varhaiskasvatuspaatos.component';
import { VardaFormListAbstractComponent } from '../../varda-form-list-abstract.component';
import { LapsiKoosteVakapaatos } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { sortByAlkamisPvm } from '../../../../../utilities/helper-functions';
import { VardaVakajarjestajaService } from '../../../../../core/services/varda-vakajarjestaja.service';

@Component({
  selector: 'app-varda-varhaiskasvatuspaatokset',
  templateUrl: './varda-varhaiskasvatuspaatokset.component.html',
  styleUrls: [
    './varda-varhaiskasvatuspaatokset.component.css',
    '../varda-lapsi-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaVarhaiskasvatuspaatoksetComponent extends VardaFormListAbstractComponent implements OnInit {
  @ViewChildren(VardaVarhaiskasvatuspaatosComponent) objectElements: QueryList<VardaVarhaiskasvatuspaatosComponent>;
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;

  varhaiskasvatuspaatosList: Array<LapsiKoosteVakapaatos> = [];
  lapsitiedotTallentaja: boolean;

  constructor(
    private lapsiService: VardaLapsiService,
    private vakajarjestajaService: VardaVakajarjestajaService
  ) {
    super();
  }

  ngOnInit() {
    const activeLapsi = this.lapsiService.activeLapsi.getValue();
    this.varhaiskasvatuspaatosList = activeLapsi.varhaiskasvatuspaatokset;
    this.lapsitiedotTallentaja = this.toimipaikkaAccess.lapsitiedot.tallentaja;

    const selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    if (activeLapsi.paos_organisaatio_oid && activeLapsi.tallentaja_organisaatio_oid !== selectedVakajarjestaja.organisaatio_oid) {
      this.lapsitiedotTallentaja = false;
    }

    this.addObjectBoolean = this.varhaiskasvatuspaatosList.length === 0;
  }

  addVarhaiskasvatuspaatos(varhaiskasvatuspaatos: LapsiKoosteVakapaatos) {
    this.varhaiskasvatuspaatosList = this.varhaiskasvatuspaatosList.filter(obj => obj.id !== varhaiskasvatuspaatos.id);
    this.varhaiskasvatuspaatosList.push(varhaiskasvatuspaatos);
    this.varhaiskasvatuspaatosList = this.varhaiskasvatuspaatosList.sort(sortByAlkamisPvm);
    this.updateActiveLapsi();
  }

  deleteVarhaiskasvatuspaatos(objectId: number) {
    this.varhaiskasvatuspaatosList = this.varhaiskasvatuspaatosList.filter(obj => obj.id !== objectId);
    this.updateActiveLapsi();
  }

  updateActiveLapsi() {
    const activeLapsi = this.lapsiService.activeLapsi.getValue();
    this.lapsiService.activeLapsi.next({...activeLapsi, varhaiskasvatuspaatokset: this.varhaiskasvatuspaatosList});
  }
}
