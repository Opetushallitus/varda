import { Component, OnInit } from '@angular/core';
import { HuoltajanLapsiDTO } from '../../../utilities/models/dto/huoltajan-lapsi-dto';
import { HuoltajaApiService } from '../../../services/huoltaja-api.service';
import { LoginService } from 'varda-shared';
import { MatDialog } from '@angular/material/dialog';
import { ContactDialogComponent } from '../contact-dialog/contact-dialog.component';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { LapsiDTO } from '../../../utilities/models/dto/lapsi-dto';

@Component({
  selector: 'app-huoltaja-frontpage',
  templateUrl: './huoltaja-frontpage.component.html',
  styleUrls: ['./huoltaja-frontpage.component.css']
})
export class HuoltajaFrontpageComponent {
  lapsi: HuoltajanLapsiDTO;
  fetchError: boolean;
  translation = HuoltajaTranslations;

  constructor(
    private apiService: HuoltajaApiService,
    private dialog: MatDialog,
    private loginService: LoginService
  ) {
    this.apiService.getHuoltajanLapsi(loginService.currentUserInfo.henkilo_oid).subscribe((data: HuoltajanLapsiDTO) => {
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
    const nullReplacement = 'SORT';
    const lapsetOneByOne: Array<LapsiDTO> = [];
    data.lapset.forEach(lapsi => {
      lapsi.varhaiskasvatuspaatokset.forEach(vakapaatos => {
        const lapsiByPaatos: LapsiDTO = { ...lapsi, varhaiskasvatuspaatos: vakapaatos, varhaiskasvatuspaatokset: null };
        lapsetOneByOne.push(lapsiByPaatos);
      });
    });

    lapsetOneByOne.sort((a, b) => b.varhaiskasvatuspaatos.alkamis_pvm.localeCompare(a.varhaiskasvatuspaatos.alkamis_pvm));
    lapsetOneByOne.sort((a, b) => {
      const sortByA = a.varhaiskasvatuspaatos.paattymis_pvm || nullReplacement;
      const sortByB = b.varhaiskasvatuspaatos.paattymis_pvm || nullReplacement;
      return sortByB.localeCompare(sortByA);
    });

    data.lapset = lapsetOneByOne;
    return data;
  }
}
