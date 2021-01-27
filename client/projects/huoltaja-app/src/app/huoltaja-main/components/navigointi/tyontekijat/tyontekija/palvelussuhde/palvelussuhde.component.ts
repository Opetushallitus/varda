import { Component, Input, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { PalvelussuhdeDTO, } from 'projects/huoltaja-app/src/app/utilities/models/dto/tyontekija-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { KoodistoEnum } from 'varda-shared';

@Component({
  selector: 'app-palvelussuhde',
  templateUrl: './palvelussuhde.component.html',
  styleUrls: ['./palvelussuhde.component.css']
})
export class PalvelussuhdeComponent implements OnInit {
  @Input() palvelussuhde: PalvelussuhdeDTO;
  i18n = HuoltajaTranslations;
  koodistoEnum = KoodistoEnum;
  tyoskentelypaikatList: string;
  expanded: boolean;
  kiertavaTyontekijaText: string;
  constructor(private translateService: TranslateService) {
    this.translateService.get(this.i18n.tyoskentelypaikka_kiertava_kytkin).subscribe(translation => this.kiertavaTyontekijaText = translation);
  }

  ngOnInit(): void {
    const tyoskentelypaikat = new Set(this.palvelussuhde.tyoskentelypaikat.map(tyoskentelypaikka => tyoskentelypaikka.toimipaikka_nimi || this.kiertavaTyontekijaText));
    const tyoskentelypaikatList = [];
    tyoskentelypaikat.forEach(tyoskentelypaikka => tyoskentelypaikatList.push(tyoskentelypaikka));

    this.tyoskentelypaikatList = tyoskentelypaikatList.join(', ');
  }

  togglePanel(expand: boolean) {
    this.expanded = expand;
  }

}
