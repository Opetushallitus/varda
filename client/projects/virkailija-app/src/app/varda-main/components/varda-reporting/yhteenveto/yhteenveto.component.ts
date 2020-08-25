import { Component, Input, OnInit } from '@angular/core';
import { VardaVakajarjestajaYhteenvetoDTO } from '../../../../utilities/models/dto/varda-vakajarjestaja-yhteenveto-dto.model';
import { Observable } from 'rxjs';
import { VardaApiWrapperService } from '../../../../core/services/varda-api-wrapper.service';

interface YhteenvetoElement { name: string; value: number; status: string; }

@Component({
  selector: 'app-yhteenveto',
  templateUrl: './yhteenveto.component.html',
  styleUrls: ['./yhteenveto.component.css']
})
export class YhteenvetoComponent implements OnInit {

  @Input() vakajarjestajaId: string;

  yhteenveto: VardaVakajarjestajaYhteenvetoDTO;

  datasourceLapset: Array<YhteenvetoElement> = [];
  datasourceToimipaikat: Array<YhteenvetoElement> = [];
  datasourceTyontekijat: Array<YhteenvetoElement> = [];

  displayedColumns = ['name', 'value'];

  constructor(private vardaApiWrapperService: VardaApiWrapperService) { }

  ngOnInit() {
    this.fetchYhteenveto();
  }

  fetchYhteenveto(): void {
    this.getYhteenvetoForReporting().subscribe(resp => {
      this.yhteenveto = { ...resp };
      this.datasourceLapset = [
        this.createDatasourceElement('lapset_lkm'),
        this.createDatasourceElement('lapset_maksutieto_voimassaoleva'),
        this.createDatasourceElement('lapset_vakapaatos_voimassaoleva'),
        this.createDatasourceElement('lapset_vakasuhde_voimassaoleva'),
        this.createDatasourceElement('lapset_vuorohoidossa'),
        this.createDatasourceElement('lapset_palveluseteli_ja_ostopalvelu'),
      ];
      this.datasourceToimipaikat = [
        this.createDatasourceElement('toimipaikat_voimassaolevat'),
        this.createDatasourceElement('toimipaikat_paattyneet'),
        this.createDatasourceElement('toimintapainotukset_maara'),
        this.createDatasourceElement('kielipainotukset_maara'),
      ];
      this.datasourceTyontekijat = [
        this.createDatasourceElement('tyontekijat_lkm'),
        this.createDatasourceElement('palvelussuhteet_voimassaoleva'),
        this.createDatasourceElement('varhaiskasvatusalan_tutkinnot'),
        this.createDatasourceElement('tyoskentelypaikat_kelpoiset'),
        this.createDatasourceElement('taydennyskoulutukset_kuluva_vuosi'),
        this.createDatasourceElement('tilapainen_henkilosto_maara_kuluva_vuosi'),
        this.createDatasourceElement('tilapainen_henkilosto_tunnit_kuluva_vuosi'),
      ];
    });
  }

  createDatasourceElement(label: string): YhteenvetoElement {
    return {
      name: 'label.yhteenveto.' + label.replace(/_/g, '-'),
      value: this.yhteenveto[label],
      status: '',
    };
  }

  getYhteenvetoForReporting(): Observable<VardaVakajarjestajaYhteenvetoDTO> {
    return this.vardaApiWrapperService.getYhteenvetoByVakajarjestaja(this.vakajarjestajaId);
  }
}
