import { Component, Input, OnInit } from '@angular/core';
import { HenkiloListErrorDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-henkilo-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { KoodistoEnum } from 'varda-shared';

@Component({
  selector: 'app-varda-henkilo-form-error-list',
  templateUrl: './varda-henkilo-form-error-list.component.html',
  styleUrls: ['./varda-henkilo-form-error-list.component.css']
})
export class VardaHenkiloFormErrorListComponent implements OnInit {
  @Input() errors: Array<HenkiloListErrorDTO>;
  koodistoEnum = KoodistoEnum;
  i18n = VirkailijaTranslations;

  constructor() { }

  ngOnInit(): void {
  }

}
