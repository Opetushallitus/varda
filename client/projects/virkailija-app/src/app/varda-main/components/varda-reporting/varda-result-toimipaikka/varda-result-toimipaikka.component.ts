import { Component, ElementRef, Input, OnChanges, ViewChild } from '@angular/core';
import { KoodistoEnum } from 'varda-shared';
import { VardaApiService } from '../../../../core/services/varda-api.service';
import { ToimipaikkaKooste } from '../../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaDateService } from '../../../services/varda-date.service';
import { VardaResultAbstractComponent } from '../varda-result-abstract.component';

@Component({
  selector: 'app-varda-result-toimipaikka',
  templateUrl: './varda-result-toimipaikka.component.html',
  styleUrls: ['./varda-result-toimipaikka.component.css']
})
export class VardaResultToimipaikkaComponent extends VardaResultAbstractComponent implements OnChanges {
  @Input() toimipaikkaId: number;
  @ViewChild('scrollTo') scrollTo: ElementRef<HTMLElement>;

  koodistoEnum = KoodistoEnum;
  toimipaikkaKooste: ToimipaikkaKooste = null;

  constructor(
    private vardaApiService: VardaApiService,
    dateService: VardaDateService
  ) {
    super(dateService);
  }

  ngOnChanges() {
    this.fetchToimipaikka(this.toimipaikkaId);
  }

  fetchToimipaikka(id: number) {
    this.vardaApiService.getToimipaikkaKooste(id).subscribe(data => {
      this.toimipaikkaKooste = data;
      this.scrollTo.nativeElement.scrollIntoView({behavior: 'smooth', block: 'start'});
    });
  }
}
