import { Component, Inject } from '@angular/core';
import { MatLegacyDialogRef as MatDialogRef, MAT_LEGACY_DIALOG_DATA as MAT_DIALOG_DATA } from '@angular/material/legacy-dialog';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';

@Component({
  selector: 'app-tyontekijatiedot-contact-dialog',
  templateUrl: './tyontekijatiedot-contact-dialog.component.html',
  styleUrls: ['./tyontekijatiedot-contact-dialog.component.css', '../contact-dialog.component.css']
})
export class TyontekijatiedotContactDialogComponent {
  i18n = HuoltajaTranslations;

  constructor(
    private dialogRef: MatDialogRef<TyontekijatiedotContactDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any) { }

  closeDialog() {
    this.dialogRef.close();
  }
}
