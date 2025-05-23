import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';
import { VardaTiedonsiirtoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tiedonsiirto-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { KoodistoEnum } from 'varda-shared';

export interface TiedonsiirtoDialogData {
  tiedonsiirto: VardaTiedonsiirtoDTO;
}

@Component({
  selector: 'app-tiedonsiirto-modal',
  templateUrl: './tiedonsiirto-dialog.component.html',
  styleUrls: ['./tiedonsiirto-dialog.component.css']
})
export class TiedonsiirtoDialogComponent {
  i18n = VirkailijaTranslations;
  koodistoEnum = KoodistoEnum;
  tiedonsiirto: VardaTiedonsiirtoDTO;

  constructor(@Inject(MAT_DIALOG_DATA) private data: TiedonsiirtoDialogData) {
    this.tiedonsiirto = data.tiedonsiirto;

  }

  toJSON(jsonString: string) {
    try {
      return JSON.parse(jsonString);
    } catch (e) {
      console.log(e);
      return undefined;
    }
  }
}
