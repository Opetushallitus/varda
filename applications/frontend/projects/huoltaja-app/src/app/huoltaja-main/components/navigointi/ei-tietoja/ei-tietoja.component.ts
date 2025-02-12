import { Component } from '@angular/core';
import { HuoltajaApiService } from 'projects/huoltaja-app/src/app/services/huoltaja-api.service';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { Observable } from 'rxjs';
import { UserHuollettavaDTO } from 'varda-shared';

@Component({
  selector: 'app-ei-tietoja',
  templateUrl: './ei-tietoja.component.html',
  styleUrls: ['./ei-tietoja.component.css']
})
export class EiTietojaComponent {
  i18n = HuoltajaTranslations;
  henkilot$: Observable<Array<UserHuollettavaDTO>>;

  constructor(private huoltajaService: HuoltajaApiService) {
    this.henkilot$ = this.huoltajaService.getHenkilot();
  }

}
