import { Component, OnInit } from '@angular/core';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { HenkiloListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';
import { VardaHenkiloListComponent } from '../../../varda-main-frame/varda-henkilo-list/varda-henkilo-list.component';

@Component({
  selector: 'app-puutteelliset-henkilot-list',
  templateUrl: './puutteelliset-henkilot-list.component.html',
  styleUrls: ['./puutteelliset-henkilot-list.component.css', '../../../varda-main-frame/varda-henkilo-list/varda-henkilo-list.component.css']
})
export class PuutteellisetHenkilotListComponent extends VardaHenkiloListComponent implements OnInit {

  constructor(protected vakajarjestajService: VardaVakajarjestajaService) {
    super(vakajarjestajService);
  }

  ngOnInit(): void {
  }

  clickErrorItem(henkilo: HenkiloListDTO) {
    this.openErrorForm.emit(henkilo);
  }
}
