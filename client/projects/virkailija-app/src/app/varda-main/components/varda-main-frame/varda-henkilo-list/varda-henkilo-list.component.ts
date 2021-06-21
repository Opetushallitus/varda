import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { HenkiloRooliEnum } from 'projects/virkailija-app/src/app/utilities/models/enums/henkilorooli.enum';
import { HenkiloListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { LapsiListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-lapsi-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { KoodistoEnum } from 'varda-shared';

@Component({
  selector: 'app-varda-henkilo-list',
  templateUrl: './varda-henkilo-list.component.html',
  styleUrls: ['./varda-henkilo-list.component.css']
})
export class VardaHenkiloListComponent implements OnInit {
  @Input() henkiloList: Array<HenkiloListDTO>;
  @Input() henkiloRooli: HenkiloRooliEnum;
  @Output() openHenkiloForm = new EventEmitter<LapsiListDTO | TyontekijaListDTO>(true);
  i18n = VirkailijaTranslations;
  koodistoEnum = KoodistoEnum;
  selectedVakajarjestaja: VardaVakajarjestajaUi;

  constructor(
    protected vakajarjestajService: VardaVakajarjestajaService
  ) {
    this.selectedVakajarjestaja = this.vakajarjestajService.getSelectedVakajarjestaja();
  }

  ngOnInit() {
    if (this.henkiloRooli === HenkiloRooliEnum.tyontekija) {
      this.initTehtavanimikkeet();
    }
  }

  clickItem(henkilo: HenkiloListDTO) {
    const suhdeToCheck = this.henkiloRooli === HenkiloRooliEnum.lapsi ? 'lapset' : 'tyontekijat';
    henkilo.expanded = henkilo[suhdeToCheck].length !== 1;
    if (!henkilo.expanded) {
      this.openItem(henkilo[suhdeToCheck][0], henkilo);
    }
  }

  openItem(henkilonSuhde: LapsiListDTO | TyontekijaListDTO, henkilo: HenkiloListDTO) {
    henkilonSuhde.henkilo_id = henkilo.id;
    henkilonSuhde.henkilo_oid = henkilo.henkilo_oid;
    henkilonSuhde.etunimet = henkilo.etunimet;
    henkilonSuhde.sukunimi = henkilo.sukunimi;
    this.openHenkiloForm.emit(henkilonSuhde);
  }

  getPaosText(suhde: LapsiListDTO) {
    if (suhde.oma_organisaatio_oid) {
      return suhde.oma_organisaatio_oid === this.selectedVakajarjestaja.organisaatio_oid ? suhde.paos_organisaatio_nimi : suhde.oma_organisaatio_nimi;
    }

  }

  initTehtavanimikkeet() {
    this.henkiloList.forEach(henkilo => henkilo.tyontekijat.forEach(tyontekija => {
      const tehtavanimikkeet = new Set(tyontekija.tyoskentelypaikat.sort(
        (a, b) => b.alkamis_pvm.localeCompare(a.alkamis_pvm)
      ).map(tyopaikka => tyopaikka.tehtavanimike_koodi));

      tyontekija.tehtavanimikkeet = Array.from(tehtavanimikkeet);
    }));
  }
}
