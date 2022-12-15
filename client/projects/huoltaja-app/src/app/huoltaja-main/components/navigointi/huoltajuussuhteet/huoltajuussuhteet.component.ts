import { Component } from '@angular/core';
import { MatLegacyDialog as MatDialog } from '@angular/material/legacy-dialog';
import { HuoltajaApiService } from 'projects/huoltaja-app/src/app/services/huoltaja-api.service';
import { HuoltajatiedotSimpleDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/huoltajuussuhde-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { Observable } from 'rxjs';
import { ContactDialogComponent } from '../../utility-components/contact-dialog/contact-dialog.component';

@Component({
  selector: 'app-huoltajuussuhteet',
  templateUrl: './huoltajuussuhteet.component.html',
  styleUrls: ['./huoltajuussuhteet.component.css']
})
export class HuoltajuussuhteetComponent {
  huoltajatiedot$: Observable<HuoltajatiedotSimpleDTO>;
  i18n = HuoltajaTranslations;

  constructor(
    private huoltajaApiService: HuoltajaApiService,
    private dialog: MatDialog
  ) {
    this.huoltajatiedot$ = this.huoltajaApiService.getHuoltajatiedot();
  }

  openDialog(title: string, content: string) {
    this.dialog.open(ContactDialogComponent, { data: { title, content }, autoFocus: false });
  }
}
