import { Component, ElementRef, Input, OnChanges, ViewChild } from '@angular/core';
import { TyontekijaKooste } from '../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaApiService } from '../../../../core/services/varda-api.service';
import { KoodistoEnum, VardaDateService } from 'varda-shared';
import { UserAccess } from '../../../../utilities/models/varda-user-access.model';
import { VardaResultAbstractComponent } from '../varda-result-abstract.component';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';

@Component({
    selector: 'app-varda-result-tyontekija',
    templateUrl: './varda-result-tyontekija.component.html',
    styleUrls: ['./varda-result-tyontekija.component.css'],
    standalone: false
})
export class VardaResultTyontekijaComponent extends VardaResultAbstractComponent implements OnChanges {
  @Input() tyontekijaId: number;
  @Input() userAccess: UserAccess;
  @ViewChild('scrollTo') scrollTo: ElementRef<HTMLElement>;

  koodistoEnum = KoodistoEnum;
  tyontekijaKooste: TyontekijaKooste = null;

  constructor(
    private koosteService: VardaKoosteApiService,
    private vardaApiService: VardaApiService,
    dateService: VardaDateService,
  ) {
    super(dateService);
  }

  ngOnChanges() {
    this.fetchTyontekija(this.tyontekijaId);
  }

  fetchTyontekija(id: number) {
    this.koosteService.getTyontekijaKooste(id).subscribe(data => {
      this.tyontekijaKooste = data;
      this.scrollTo.nativeElement.scrollIntoView({behavior: 'smooth', block: 'start'});
    });
  }
}
