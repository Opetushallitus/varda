import { Component, Input, OnInit } from '@angular/core';
import { HuoltajuussuhdeDTO, MaksutietoDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/huoltajuussuhde-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { KoodistoEnum } from 'varda-shared';

@Component({
  selector: 'app-maksutieto',
  templateUrl: './maksutieto.component.html',
  styleUrls: ['./maksutieto.component.css']
})
export class MaksutietoComponent implements OnInit {
  @Input() huoltajuussuhde: HuoltajuussuhdeDTO;
  @Input() maksutieto: MaksutietoDTO;
  i18n = HuoltajaTranslations;
  koodistoEnum = KoodistoEnum;
  expanded = false;
  lapsenNimi: string;

  constructor() { }

  ngOnInit(): void {
    this.lapsenNimi = `${this.huoltajuussuhde.lapsi_sukunimi}, ${this.huoltajuussuhde.lapsi_etunimet}`;
  }

}
