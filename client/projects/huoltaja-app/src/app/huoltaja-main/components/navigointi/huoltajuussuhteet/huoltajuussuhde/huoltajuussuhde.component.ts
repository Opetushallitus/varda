import { Component, Input, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { HuoltajaApiService } from 'projects/huoltaja-app/src/app/services/huoltaja-api.service';
import { HuoltajuussuhdeDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/huoltajuussuhde-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { HuoltajuussuhteetContactDialogComponent } from '../../../utility-components/contact-dialog/huoltajuussuhteet-contact-dialog/huoltajuussuhteet-contact-dialog.component';

@Component({
  selector: 'app-huoltajuussuhde',
  templateUrl: './huoltajuussuhde.component.html',
  styleUrls: ['./huoltajuussuhde.component.css']
})
export class HuoltajuussuhdeComponent implements OnInit {
  @Input() huoltajuussuhde: HuoltajuussuhdeDTO;
  i18n = HuoltajaTranslations;

  constructor(private dialog: MatDialog, private huoltajaApiService: HuoltajaApiService) { }

  ngOnInit(): void {
    this.huoltajaApiService.sortByAlkamisPaattymisPvm(this.huoltajuussuhde.maksutiedot);
  }

  openDialog(huoltajuussuhde?: HuoltajuussuhdeDTO) {
    this.dialog.open(HuoltajuussuhteetContactDialogComponent, {
      data: {
        email: huoltajuussuhde?.yhteysosoite,
        toimija: huoltajuussuhde?.vakatoimija_nimi || huoltajuussuhde?.oma_organisaatio_nimi,
        lakkautettu: huoltajuussuhde?.aktiivinen_toimija === false
      },
      autoFocus: false
    });
  }
}
