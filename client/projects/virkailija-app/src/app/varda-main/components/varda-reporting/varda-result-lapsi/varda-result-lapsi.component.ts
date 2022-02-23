import { Component, ElementRef, Input, OnChanges, ViewChild } from '@angular/core';
import { VardaApiService } from '../../../../core/services/varda-api.service';
import { LapsiKooste } from '../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaUtilityService } from '../../../../core/services/varda-utility.service';
import { UserAccess } from '../../../../utilities/models/varda-user-access.model';
import { KoodistoEnum, VardaDateService } from 'varda-shared';
import { VardaResultAbstractComponent } from '../varda-result-abstract.component';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';
import { kunnallisetJarjestamismuodot } from '../../varda-henkilo-form/varda-lapsi-form/varda-varhaiskasvatuspaatokset/varda-varhaiskasvatuspaatos/varda-varhaiskasvatuspaatos.component';

@Component({
  selector: 'app-varda-result-lapsi',
  templateUrl: './varda-result-lapsi.component.html',
  styleUrls: ['./varda-result-lapsi.component.css']
})
export class VardaResultLapsiComponent extends VardaResultAbstractComponent implements OnChanges {
  @Input() lapsiId: number;
  @Input() userAccess: UserAccess;
  @ViewChild('scrollTo') scrollTo: ElementRef<HTMLElement>;

  koodistoEnum = KoodistoEnum;
  lapsiKooste: LapsiKooste = null;

  constructor(
    private koosteService: VardaKoosteApiService,
    private vardaApiService: VardaApiService,
    private vardaUtilityService: VardaUtilityService,
    dateService: VardaDateService
  ) {
    super(dateService);
  }

  ngOnChanges() {
    this.fetchToimipaikanLapsi(this.lapsiId);
  }

  fetchToimipaikanLapsi(id: number): void {
    this.koosteService.getLapsiKooste(id).subscribe(data => {
      this.lapsiKooste = data;
      this.scrollTo.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  getVakasuhteetForVakapaatos(id: number) {
    return this.lapsiKooste.varhaiskasvatussuhteet.filter(vakasuhde => String(id) === this.vardaUtilityService.parseIdFromUrl(vakasuhde.varhaiskasvatuspaatos));
  }

  isKunnallinenJarjestamismuoto(jarjetamismuoto: string) {
    return kunnallisetJarjestamismuodot.includes(jarjetamismuoto.toLocaleUpperCase());
  }
}
