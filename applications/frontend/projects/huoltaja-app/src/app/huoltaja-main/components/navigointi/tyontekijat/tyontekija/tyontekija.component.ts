import { Component, Input, ViewEncapsulation } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { TyontekijaDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/tyontekija-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import {
  TyontekijatiedotContactDialogComponent
} from '../../../utility-components/contact-dialog/tyontekijatiedot-contact-dialog/tyontekijatiedot-contact-dialog.component';

@Component({
  selector: 'app-tyontekija',
  templateUrl: './tyontekija.component.html',
  styleUrls: ['./tyontekija.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class TyontekijaComponent {
  @Input() tyontekija: TyontekijaDTO;
  @Input() first: boolean;
  i18n = HuoltajaTranslations;

  constructor(private dialog: MatDialog) { }


  openDialog(tyontekija?: TyontekijaDTO) {
    this.dialog.open(TyontekijatiedotContactDialogComponent, {
      data: {
        email: tyontekija?.yhteysosoite,
        toimija: tyontekija?.vakajarjestaja_nimi,
        lakkautettu: tyontekija?.aktiivinen_toimija === false
      },
      autoFocus: false
    });
  }
}
