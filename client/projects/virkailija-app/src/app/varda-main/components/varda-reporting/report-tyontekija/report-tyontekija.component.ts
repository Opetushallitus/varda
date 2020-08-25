import { Component, ElementRef, Input, OnChanges, ViewChild } from '@angular/core';
import { TyontekijaByToimipaikkaDTO, TyontekijaKooste } from '../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaApiService } from '../../../../core/services/varda-api.service';
import { KoodistoEnum, VardaKoodistoService } from 'varda-shared';
import { VardaDateService } from '../../../services/varda-date.service';

@Component({
  selector: 'app-report-tyontekija',
  templateUrl: './report-tyontekija.component.html',
  styleUrls: ['./report-tyontekija.component.css']
})
export class ReportTyontekijaComponent implements OnChanges {
  @Input() tyontekija: TyontekijaByToimipaikkaDTO;
  @ViewChild('tyontekijaScrollTo') tyontekijaScrollTo: ElementRef<HTMLElement>;

  koodistoEnum = KoodistoEnum;
  tyontekijaKooste: TyontekijaKooste = null;

  constructor(
    private vardaApiService: VardaApiService,
    private koodistoService: VardaKoodistoService,
    private dateService: VardaDateService,
  ) {}

  ngOnChanges() {
    this.fetchTyontekija(this.tyontekija.tyontekija_id);
  }

  fetchTyontekija(id: number) {
    this.vardaApiService.getTyontekijaKooste(id).subscribe(data => {
      this.tyontekijaKooste = data;
      this.tyontekijaScrollTo.nativeElement.scrollIntoView({behavior: 'smooth', block: 'start'});
    });
  }

  getCodeFromKoodistoService(koodistoName: KoodistoEnum, code: string) {
    return this.koodistoService.getCodeValueFromKoodisto(koodistoName, code);
  }

  getDateDisplayValue(date: string): string {
    return this.dateService.getDateDisplayValue(date);
  }

  getDateRangeDisplayValue(startDate: string, endDate: string): string {
    return this.dateService.getDateRangeDisplayValue(startDate, endDate);
  }
}
