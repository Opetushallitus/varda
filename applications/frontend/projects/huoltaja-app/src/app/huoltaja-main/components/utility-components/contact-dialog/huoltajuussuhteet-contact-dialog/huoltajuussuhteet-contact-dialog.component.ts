import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';

@Component({
    selector: 'app-huoltajuussuhteet-contact-dialog',
    templateUrl: './huoltajuussuhteet-contact-dialog.component.html',
    styleUrls: ['./huoltajuussuhteet-contact-dialog.component.css', '../contact-dialog.component.css'],
    standalone: false
})
export class HuoltajuussuhteetContactDialogComponent {
  i18n = HuoltajaTranslations;

  constructor(
    private dialogRef: MatDialogRef<HuoltajuussuhteetContactDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any) { }


  closeDialog() {
    this.dialogRef.close();
  }
}
