import { Component, OnDestroy, OnInit } from '@angular/core';
import { HuoltajanLapsiDTO } from '../../../utilities/models/dto/huoltajan-lapsi-dto';
import { HuoltajaApiService } from '../../../services/huoltaja-api.service';
import { LoginService } from 'varda-shared';
import { MatDialog } from '@angular/material/dialog';
import { ContactDialogComponent } from '../contact-dialog/contact-dialog.component';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { LapsiDTO } from '../../../utilities/models/dto/lapsi-dto';
import { mergeMap, take } from 'rxjs/operators';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-huoltaja-frontpage',
  templateUrl: './huoltaja-frontpage.component.html',
  styleUrls: ['./huoltaja-frontpage.component.css']
})
export class HuoltajaFrontpageComponent {
  lapsi: HuoltajanLapsiDTO;
  fetchError: boolean;
  translation = HuoltajaTranslations;
  subscriptions: Array<Subscription> = [];
  constructor(
    private apiService: HuoltajaApiService,
    private dialog: MatDialog,
    private loginService: LoginService
  ) {
    this.loginService.getCurrentUser().pipe(
      mergeMap(currentUser => this.apiService.getHuoltajanLapsi(currentUser.henkilo_oid)),
      take(1)
    ).subscribe((data: HuoltajanLapsiDTO) => {
      this.lapsi = this.sortVakapaatokset(data);
      this.apiService.setCurrentUser(data);

    }, (error: any) => {
      console.error(error.message);
      this.fetchError = true;
      this.apiService.setCurrentUser({ henkilo: {} });
    });
  }

  openDialog(title: string, content: string) {
    this.dialog.open(ContactDialogComponent, { data: { title: title, content: content } });
  }

  sortVakapaatokset(data: HuoltajanLapsiDTO) {
    const lapsetOneByOne: Array<LapsiDTO> = [];
    data.lapset.forEach(lapsi => {
      lapsi.varhaiskasvatuspaatokset.forEach(vakapaatos => {
        const lapsiByPaatos: LapsiDTO = { ...lapsi, varhaiskasvatuspaatos: vakapaatos, varhaiskasvatuspaatokset: null };
        lapsetOneByOne.push(lapsiByPaatos);
      });
    });

    lapsetOneByOne.sort((a, b) => {
      const sortA = a.varhaiskasvatuspaatos;
      const sortB = b.varhaiskasvatuspaatos;

      const sortByA = sortA.paattymis_pvm ? `${sortA.alkamis_pvm}x${sortA.paattymis_pvm}` : `x${sortA.alkamis_pvm}`;
      const sortByB = sortB.paattymis_pvm ? `${sortB.alkamis_pvm}x${sortB.paattymis_pvm}` : `x${sortB.alkamis_pvm}`;
      return sortByB.localeCompare(sortByA);
    });


    data.lapset = lapsetOneByOne;
    return data;
  }
}
