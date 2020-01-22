import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {VardaToimipaikkaYhteenvetoDTO} from '../../../../utilities/models/dto/varda-toimipaikka-yhteenveto-dto.model';
import {Observable} from 'rxjs';
import {VardaApiWrapperService} from '../../../../core/services/varda-api-wrapper.service';

interface YhteenvetoElement {tieto: string; lukumaara: number; status: string; }

@Component({
  selector: 'app-yhteenveto',
  templateUrl: './yhteenveto.component.html',
  styleUrls: ['./yhteenveto.component.css']
})
export class YhteenvetoComponent implements OnInit {

  @Input() toimipaikkaId: string;
  @Output() uiLoading: EventEmitter<boolean>;

  yhteenveto: VardaToimipaikkaYhteenvetoDTO;

  datasourceLapset: Array<YhteenvetoElement>;
  datasourceToimipaikat: Array<YhteenvetoElement>;

  displayedColumns: string[];

  constructor(private vardaApiWrapperService: VardaApiWrapperService) {
    this.uiLoading = new EventEmitter<boolean>(true);
  }

  ngOnInit() {
    this.datasourceLapset = [];
    this.displayedColumns = ['tieto', 'lukumaara'];
    this.yhteenveto = {
      vakajarjestaja_nimi: null,
      lapset_lkm: null,
      lapset_maksutieto_voimassaoleva: null,
      lapset_vakapaatos_voimassaoleva: null,
      lapset_vakasuhde_voimassaoleva: null,
      lapset_vuorohoidossa: null,
      lapset_palveluseteli_ja_ostopalvelu: null,
      toimipaikat_voimassaolevat: null,
      toimipaikat_paattyneet: null,
      toimintapainotukset_maara: null,
      kielipainotukset_maara: null,
    };
    this.fetchYhteenveto();
  }

  fetchYhteenveto(): void {
    this.uiLoading.emit(true);
    this.getYhteenvetoForReporting().subscribe(resp => {
      this.yhteenveto = {...resp};
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
      this.uiLoading.emit(false);
    });
  }

  createDatasourceElement(label: string): YhteenvetoElement {
    return {
      tieto: 'label.yhteenveto.' + label.replace(/_/g, '-'),
      lukumaara: this.yhteenveto[label],
      status: '',
    };
  }

  getYhteenvetoForReporting(): Observable<VardaToimipaikkaYhteenvetoDTO> {
    return this.vardaApiWrapperService.getYhteenvetoByToimipaikka(this.toimipaikkaId);
  }

}
