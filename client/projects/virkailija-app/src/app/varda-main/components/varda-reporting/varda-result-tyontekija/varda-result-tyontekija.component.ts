import { Component, ElementRef, Input, OnChanges, ViewChild } from '@angular/core';
import {
  TyontekijaKooste,
  TyontekijaTaydennyskoulutusCombined
} from '../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaApiService } from '../../../../core/services/varda-api.service';
import { KoodistoEnum, VardaDateService } from 'varda-shared';
import { UserAccess } from '../../../../utilities/models/varda-user-access.model';
import { VardaResultAbstractComponent } from '../varda-result-abstract.component';
import { VardaKoosteApiService } from 'projects/virkailija-app/src/app/core/services/varda-kooste-api.service';

@Component({
  selector: 'app-varda-result-tyontekija',
  templateUrl: './varda-result-tyontekija.component.html',
  styleUrls: ['./varda-result-tyontekija.component.css']
})
export class VardaResultTyontekijaComponent extends VardaResultAbstractComponent implements OnChanges {
  @Input() tyontekijaId: number;
  @Input() userAccess: UserAccess;
  @ViewChild('scrollTo') scrollTo: ElementRef<HTMLElement>;

  koodistoEnum = KoodistoEnum;
  tyontekijaKooste: TyontekijaKooste = null;
  taydennyskoulutusList: Array<TyontekijaTaydennyskoulutusCombined> = [];

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
      this.taydennyskoulutusList = [];

      // Combine TaydennyskoulutusTyontekija objects by ID
      data.taydennyskoulutukset.forEach(taydennyskoulutus => {
        const existingTaydennyskoulutus = this.taydennyskoulutusList.find(tk => tk.id === taydennyskoulutus.id);
        if (existingTaydennyskoulutus) {
          existingTaydennyskoulutus.tehtavanimikeList.push(taydennyskoulutus.tehtavanimike_koodi);
        } else {
          this.taydennyskoulutusList.push({
            ...taydennyskoulutus,
            tehtavanimikeList: [taydennyskoulutus.tehtavanimike_koodi]
          });
        }
      });
      this.scrollTo.nativeElement.scrollIntoView({behavior: 'smooth', block: 'start'});
    });
  }
}
