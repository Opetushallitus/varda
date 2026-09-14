import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';

@Component({
    selector: 'app-tyontekijatiedot-contact-dialog',
    templateUrl: './tyontekijatiedot-contact-dialog.component.html',
    styleUrls: ['./tyontekijatiedot-contact-dialog.component.css', '../contact-dialog.component.css'],
    standalone: false
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
