import { Component, OnInit } from '@angular/core';
import { VardaVakajarjestajaYhteenvetoDTO } from '../../../../utilities/models/dto/varda-vakajarjestaja-yhteenveto-dto.model';
import { Observable } from 'rxjs';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';

interface YhteenvetoElement {
  name: string;
  value: number;
  status: string;
}

@Component({
  selector: 'app-varda-yhteenveto',
  templateUrl: './varda-yhteenveto.component.html',
  styleUrls: ['./varda-yhteenveto.component.css']
})
export class VardaYhteenvetoComponent implements OnInit {
  i18n = VirkailijaTranslations;

  datasourceLapset: Array<YhteenvetoElement> = [];
  datasourceToimipaikat: Array<YhteenvetoElement> = [];
  datasourceTyontekijat: Array<YhteenvetoElement> = [];
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  displayedColumns = ['name', 'value'];

  constructor(
    private koosteService: VardaKoosteApiService,
    private vakajarjestajService: VardaVakajarjestajaService
  ) {
    this.selectedVakajarjestaja = this.vakajarjestajService.getSelectedVakajarjestaja();
   }

  ngOnInit() {
    this.fetchYhteenveto();
  }

  fetchYhteenveto(): void {
    this.getYhteenvetoForReporting().subscribe(yhteenveto => {
      this.datasourceLapset = [
        [this.i18n.yhteenveto_lapset_lkm, yhteenveto.lapset_lkm],
        [this.i18n.yhteenveto_lapset_vakapaatos_voimassaoleva, yhteenveto.lapset_vakapaatos_voimassaoleva],
        [this.i18n.yhteenveto_lapset_vakasuhde_voimassaoleva, yhteenveto.lapset_vakasuhde_voimassaoleva],
        [this.i18n.yhteenveto_lapset_vuorohoidossa, yhteenveto.lapset_vuorohoidossa],
        [this.i18n.yhteenveto_lapset_palveluseteli_ja_ostopalvelu, yhteenveto.lapset_palveluseteli_ja_ostopalvelu],
        [this.i18n.yhteenveto_lapset_maksutieto_voimassaoleva, yhteenveto.lapset_maksutieto_voimassaoleva]
      ].map(item => this.createDatasourceElement(item[0] as string, item[1] as number));

      this.datasourceToimipaikat = [
        [this.i18n.yhteenveto_toimipaikat_voimassaolevat, yhteenveto.toimipaikat_voimassaolevat],
        [this.i18n.yhteenveto_toimipaikat_paattyneet, yhteenveto.toimipaikat_paattyneet],
        [this.i18n.yhteenveto_toimintapainotukset_maara, yhteenveto.toimintapainotukset_maara],
        [this.i18n.yhteenveto_kielipainotukset_maara, yhteenveto.kielipainotukset_maara]
      ].map(item => this.createDatasourceElement(item[0] as string, item[1] as number));

      this.datasourceTyontekijat = [
        [this.i18n.yhteenveto_tyontekijat_lkm, yhteenveto.tyontekijat_lkm],
        [this.i18n.yhteenveto_palvelussuhteet_voimassaoleva, yhteenveto.palvelussuhteet_voimassaoleva],
        [this.i18n.yhteenveto_varhaiskasvatusalan_tutkinnot, yhteenveto.varhaiskasvatusalan_tutkinnot],
        [this.i18n.yhteenveto_tyoskentelypaikat_kelpoiset, yhteenveto.tyoskentelypaikat_kelpoiset],
        [this.i18n.yhteenveto_taydennyskoulutukset_kuluva_vuosi, yhteenveto.taydennyskoulutukset_kuluva_vuosi],
        [this.i18n.yhteenveto_tilapainen_henkilosto_maara_kuluva_vuosi, yhteenveto.tilapainen_henkilosto_maara_kuluva_vuosi],
        [this.i18n.yhteenveto_tilapainen_henkilosto_tunnit_kuluva_vuosi, yhteenveto.tilapainen_henkilosto_tunnit_kuluva_vuosi],
      ].map(item => this.createDatasourceElement(item[0] as string, item[1] as number));
    });
  }

  createDatasourceElement(label: string, value: number): YhteenvetoElement {
    return {
      name: label,
      value: value,
      status: '',
    };
  }

  getYhteenvetoForReporting(): Observable<VardaVakajarjestajaYhteenvetoDTO> {
    return this.koosteService.getYhteenveto(this.selectedVakajarjestaja.id);
  }
}
