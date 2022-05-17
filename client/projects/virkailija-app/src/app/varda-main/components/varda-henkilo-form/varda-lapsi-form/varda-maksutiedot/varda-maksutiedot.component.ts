import { Component, OnInit, Input, ViewChildren, QueryList } from '@angular/core';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { KoodistoDTO } from 'varda-shared';
import { VardaMaksutietoComponent } from './varda-maksutieto/varda-maksutieto.component';
import { VardaFormListAbstractComponent } from '../../varda-form-list-abstract.component';
import { LapsiKoosteMaksutieto } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { sortByAlkamisPvm } from '../../../../../utilities/helper-functions';
import { VardaVakajarjestajaService } from '../../../../../core/services/varda-vakajarjestaja.service';


@Component({
  selector: 'app-varda-maksutiedot',
  templateUrl: './varda-maksutiedot.component.html',
  styleUrls: [
    './varda-maksutiedot.component.css',
    '../varda-lapsi-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaMaksutiedotComponent extends VardaFormListAbstractComponent<LapsiKoosteMaksutieto> implements OnInit {
  @ViewChildren(VardaMaksutietoComponent) objectElements: QueryList<VardaMaksutietoComponent>;
  @Input() toimipaikkaAccess: UserAccess;

  tehtavanimikkeet: KoodistoDTO;
  maksutietoOikeus: boolean;
  selectedVakajarjestaja: VardaVakajarjestajaUi;

  constructor(
    private lapsiService: VardaLapsiService,
    private vakajarjestajaService: VardaVakajarjestajaService
  ) {
    super();
  }

  ngOnInit() {
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    this.objectList = this.lapsiService.activeLapsi.getValue().maksutiedot.sort(sortByAlkamisPvm);
    // enable maksutiedot for non-paos and your own paos-kids
    const activeLapsi = this.lapsiService.activeLapsi.getValue();
    if (!activeLapsi.oma_organisaatio_oid || activeLapsi.oma_organisaatio_oid === this.selectedVakajarjestaja.organisaatio_oid) {
      this.maksutietoOikeus = true;
    }
  }

  updateActiveObject() {
    const activeLapsi = this.lapsiService.activeLapsi.getValue();
    this.lapsiService.activeLapsi.next({...activeLapsi, maksutiedot: this.objectList});
  }
}
