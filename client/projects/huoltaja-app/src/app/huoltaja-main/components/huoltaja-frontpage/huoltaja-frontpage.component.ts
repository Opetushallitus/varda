import { Component, OnInit } from '@angular/core';
import { HuoltajanLapsiDTO } from '../../../utilities/models/dto/huoltajan-lapsi-dto';
import { HuoltajaApiService } from '../../../services/huoltaja-api.service';
import { LoginService } from 'varda-shared';
import { MatDialog } from '@angular/material/dialog';
import { ContactDialogComponent } from '../contact-dialog/contact-dialog.component';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';

@Component({
  selector: 'app-huoltaja-frontpage',
  templateUrl: './huoltaja-frontpage.component.html',
  styleUrls: ['./huoltaja-frontpage.component.css']
})
export class HuoltajaFrontpageComponent implements OnInit {
  lapsi: HuoltajanLapsiDTO;
  fetchError: boolean;
  translation = HuoltajaTranslations;

  constructor(
    private apiService: HuoltajaApiService,
    private dialog: MatDialog,
    private loginService: LoginService) {
    this.apiService.getHuoltajanLapsi(loginService.currentUserInfo.henkilo_oid).subscribe((data: HuoltajanLapsiDTO) => {
      this.lapsi = data;
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

  ngOnInit() { }
}
