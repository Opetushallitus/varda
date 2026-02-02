import { Component, OnInit } from '@angular/core';
import { VirkailijaTranslations } from '../../../../../assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaService } from '../../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';

interface YhteenvetoElement {
  name: string;
  value: number;
  tooltip: string;
  id: string;
  status: string;
}

interface YhteenvetoTuenTiedotElement {
  name: string;
  date: string;
  value: number;
  tooltip: string;
  id: string;
  status: string;
}

@Component({
    selector: 'app-varda-yhteenveto',
    templateUrl: './varda-yhteenveto.component.html',
    styleUrls: ['./varda-yhteenveto.component.css'],
    standalone: false
})
export class VardaYhteenvetoComponent implements OnInit {
  i18n = VirkailijaTranslations;

  timestamp: string;
  is_kunta: boolean;
  datasourceLapset: Array<YhteenvetoElement> = [];
  datasourceToimipaikat: Array<YhteenvetoElement> = [];
  datasourceTyontekijat: Array<YhteenvetoElement> = [];
  datasourceTuenTiedot: Array<YhteenvetoTuenTiedotElement> = [];
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  displayedColumns = ['name', 'value', 'tooltip'];
  displayedColumnsTuenTiedot = ['name', 'date', 'value', 'tooltip'];

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
    this.koosteService.getYhteenveto(this.selectedVakajarjestaja.id).subscribe(yhteenveto => {
      this.datasourceLapset = [
        [this.i18n.yhteenveto_lapset_lkm, yhteenveto.lapset_lkm, this.i18n.yhteenveto_tooltip_lapset_lkm, 'lapset_lkm'],
        [this.i18n.yhteenveto_lapset_palveluseteli_ja_ostopalvelu, yhteenveto.lapset_palveluseteli_ja_ostopalvelu,
          this.i18n.yhteenveto_tooltip_lapset_palveluseteli_ja_ostopalvelu, 'lapset_palveluseteli_ja_ostopalvelu'],
        [this.i18n.yhteenveto_lapset_vuorohoidossa, yhteenveto.lapset_vuorohoidossa,
          this.i18n.yhteenveto_tooltip_lapset_vuorohoidossa, 'lapset_vuorohoidossa'],
        [this.i18n.yhteenveto_lapset_paivittainen, yhteenveto.lapset_paivittainen,
          this.i18n.yhteenveto_tooltip_lapset_paivittainen, 'lapset_paivittainen'],
        [this.i18n.yhteenveto_lapset_kokopaivainen, yhteenveto.lapset_kokopaivainen,
          this.i18n.yhteenveto_tooltip_lapset_kokopaivainen, 'lapset_kokopaivainen'],
        [this.i18n.yhteenveto_lapset_vakapaatos_voimassaoleva, yhteenveto.lapset_vakapaatos_voimassaoleva,
          this.i18n.yhteenveto_tooltip_lapset_vakapaatos_voimassaoleva, 'lapset_vakapaatos_voimassaoleva'],
        [this.i18n.yhteenveto_lapset_vakasuhde_voimassaoleva, yhteenveto.lapset_vakasuhde_voimassaoleva,
          this.i18n.yhteenveto_tooltip_lapset_vakasuhde_voimassaoleva, 'lapset_vakasuhde_voimassaoleva'],
        [this.i18n.yhteenveto_lapset_maksutieto_voimassaoleva, yhteenveto.lapset_maksutieto_voimassaoleva,
          this.i18n.yhteenveto_tooltip_lapset_maksutieto_voimassaoleva, 'lapset_maksutieto_voimassaoleva']
      ].map(item => this.createDatasourceElement(item[0] as string, item[1] as number, item[2] as string,
        item[3] as string));

      this.datasourceToimipaikat = [
        [this.i18n.yhteenveto_toimipaikat_voimassaolevat, yhteenveto.toimipaikat_voimassaolevat,
          this.i18n.yhteenveto_tooltip_toimipaikat_voimassaolevat, 'toimipaikat_voimassaolevat'],
        [this.i18n.yhteenveto_toimipaikat_paattyneet, yhteenveto.toimipaikat_paattyneet,
          this.i18n.yhteenveto_tooltip_toimipaikat_paattyneet, 'toimipaikat_paattyneet'],
        [this.i18n.yhteenveto_toimintapainotukset_maara, yhteenveto.toimintapainotukset_maara,
          this.i18n.yhteenveto_tooltip_toimintapainotukset_maara, 'toimintapainotukset_maara'],
        [this.i18n.yhteenveto_kielipainotukset_maara, yhteenveto.kielipainotukset_maara,
          this.i18n.yhteenveto_tooltip_kielipainotukset_maara, 'kielipainotukset_maara']
      ].map(item => this.createDatasourceElement(item[0] as string, item[1] as number, item[2] as string,
        item[3] as string));

      this.datasourceTyontekijat = [
        [this.i18n.yhteenveto_tyontekijat_lkm, yhteenveto.tyontekijat_lkm,
          this.i18n.yhteenveto_tooltip_tyontekijat_lkm, 'tyontekijat_lkm'],
        [this.i18n.yhteenveto_palvelussuhteet_voimassaoleva, yhteenveto.palvelussuhteet_voimassaoleva,
          this.i18n.yhteenveto_tooltip_palvelussuhteet_voimassaoleva, 'palvelussuhteet_voimassaoleva'],
        [this.i18n.yhteenveto_palvelussuhteet_maaraaikaiset, yhteenveto.palvelussuhteet_maaraaikaiset,
          this.i18n.yhteenveto_tooltip_palvelussuhteet_maaraaikaiset, 'palvelussuhteet_maaraaikaiset'],
        [this.i18n.yhteenveto_varhaiskasvatusalan_tutkinnot, yhteenveto.varhaiskasvatusalan_tutkinnot,
          this.i18n.yhteenveto_tooltip_varhaiskasvatusalan_tutkinnot, 'varhaiskasvatusalan_tutkinnot'],
        [this.i18n.yhteenveto_tyoskentelypaikat_voimassaoleva, yhteenveto.tyoskentelypaikat_voimassaoleva,
          this.i18n.yhteenveto_tooltip_tyoskentelypaikat_voimassaoleva, 'tyoskentelypaikat_voimassaoleva'],
        [this.i18n.yhteenveto_tyoskentelypaikat_kelpoiset, yhteenveto.tyoskentelypaikat_kelpoiset,
          this.i18n.yhteenveto_tooltip_tyoskentelypaikat_kelpoiset, 'tyoskentelypaikat_kelpoiset'],
        [this.i18n.yhteenveto_pidemmat_poissaolot_voimassaoleva, yhteenveto.pidemmat_poissaolot_voimassaoleva,
          this.i18n.yhteenveto_tooltip_pidemmat_poissaolot_voimassaoleva, 'pidemmat_poissaolot_voimassaoleva'],
        [this.i18n.yhteenveto_taydennyskoulutukset_kuluva_vuosi, yhteenveto.taydennyskoulutukset_kuluva_vuosi,
          this.i18n.yhteenveto_tooltip_taydennyskoulutukset_kuluva_vuosi, 'taydennyskoulutukset_kuluva_vuosi'],
        [this.i18n.yhteenveto_vuokrattu_henkilosto_maara_kuluva_vuosi,
          yhteenveto.vuokrattu_henkilosto_maara_kuluva_vuosi,
          this.i18n.yhteenveto_tooltip_vuokrattu_henkilosto_maara_kuluva_vuosi,
          'vuokrattu_henkilosto_maara_kuluva_vuosi'],
        [this.i18n.yhteenveto_vuokrattu_henkilosto_tunnit_kuluva_vuosi,
          yhteenveto.vuokrattu_henkilosto_tunnit_kuluva_vuosi,
          this.i18n.yhteenveto_tooltip_vuokrattu_henkilosto_tunnit_kuluva_vuosi,
          'vuokrattu_henkilosto_tunnit_kuluva_vuosi'],
      ].map(item => this.createDatasourceElement(item[0] as string, item[1] as number, item[2] as string,
        item[3] as string));

      this.datasourceTuenTiedot = [
        [
          this.i18n.yhteenveto_tuen_tiedot_kunnallinen_tt_01,
          yhteenveto.tuen_tiedot_kunnallinen_tt_01_date,
          yhteenveto.tuen_tiedot_kunnallinen_tt_01,
          this.i18n.yhteenveto_tooltip_tuen_tiedot_kunnallinen_tt_01,
          'tuen_tiedot_kunnallinen_tt_01'
        ],
        [
          this.i18n.yhteenveto_tuen_tiedot_kunnallinen_tt_02,
          yhteenveto.tuen_tiedot_kunnallinen_tt_02_date,
          yhteenveto.tuen_tiedot_kunnallinen_tt_02,
          this.i18n.yhteenveto_tooltip_tuen_tiedot_kunnallinen_tt_02,
          'tuen_tiedot_kunnallinen_tt_02'
        ],
        [
          this.i18n.yhteenveto_tuen_tiedot_kunnallinen_tt_03,
          yhteenveto.tuen_tiedot_kunnallinen_tt_03_date,
          yhteenveto.tuen_tiedot_kunnallinen_tt_03,
          this.i18n.yhteenveto_tooltip_tuen_tiedot_kunnallinen_tt_03,
          'tuen_tiedot_kunnallinen_tt_03'
        ],
        [
          this.i18n.yhteenveto_tuen_tiedot_yksityinen_tt_01,
          yhteenveto.tuen_tiedot_yksityinen_tt_01_date,
          yhteenveto.tuen_tiedot_yksityinen_tt_01,
          this.i18n.yhteenveto_tooltip_tuen_tiedot_yksityinen_tt_01,
          'tuen_tiedot_yksityinen_tt_01'
        ],
        [
          this.i18n.yhteenveto_tuen_tiedot_yksityinen_tt_02,
          yhteenveto.tuen_tiedot_yksityinen_tt_02_date,
          yhteenveto.tuen_tiedot_yksityinen_tt_02,
          this.i18n.yhteenveto_tooltip_tuen_tiedot_yksityinen_tt_02,
          'tuen_tiedot_yksityinen_tt_02'
        ],
        [
          this.i18n.yhteenveto_tuen_tiedot_yksityinen_tt_03,
          yhteenveto.tuen_tiedot_yksityinen_tt_03_date,
          yhteenveto.tuen_tiedot_yksityinen_tt_03,
          this.i18n.yhteenveto_tooltip_tuen_tiedot_yksityinen_tt_03,
          'tuen_tiedot_yksityinen_tt_03'
        ]
      ].map(item => this.createTuenTiedotDatasourceElement(
        item[0] as string,
        item[1] as string,
        item[2] as number,
        item[3] as string,
        item[4] as string));

      this.is_kunta = yhteenveto.is_kunta;
      this.timestamp = yhteenveto.timestamp;
    });
  }

  createDatasourceElement(label: string, value: number, tooltip: string, id: string): YhteenvetoElement {
    return {name: label, value, tooltip, id, status: ''};
  }

  createTuenTiedotDatasourceElement(label: string, date: string, value: number, tooltip: string, id: string): YhteenvetoTuenTiedotElement {
    return {name: label, date, value, tooltip, id, status: ''};
  }
}
