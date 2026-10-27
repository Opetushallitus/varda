import { Component, ElementRef, Input, OnChanges, ViewChild } from '@angular/core';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';
import { KoodistoEnum, VardaDateService } from 'varda-shared';
import { ToimipaikkaKooste } from '../../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaResultAbstractComponent } from '../varda-result-abstract.component';

@Component({
    selector: 'app-varda-result-toimipaikka',
    templateUrl: './varda-result-toimipaikka.component.html',
    styleUrls: ['./varda-result-toimipaikka.component.css'],
    standalone: false
})
export class VardaResultToimipaikkaComponent extends VardaResultAbstractComponent implements OnChanges {
  @Input() toimipaikkaId: number;
  @ViewChild('scrollTo') scrollTo: ElementRef<HTMLElement>;

  koodistoEnum = KoodistoEnum;
  toimipaikkaKooste: ToimipaikkaKooste = null;

  constructor(
    private koosteService: VardaKoosteApiService,
    dateService: VardaDateService
  ) {
    super(dateService);
  }

  ngOnChanges() {
    this.fetchToimipaikka(this.toimipaikkaId);
  }

  fetchToimipaikka(id: number) {
    this.koosteService.getToimipaikkaKooste(id).subscribe(data => {
      this.toimipaikkaKooste = data;
      this.scrollTo.nativeElement.scrollIntoView({behavior: 'smooth', block: 'start'});
    });
  }
}
