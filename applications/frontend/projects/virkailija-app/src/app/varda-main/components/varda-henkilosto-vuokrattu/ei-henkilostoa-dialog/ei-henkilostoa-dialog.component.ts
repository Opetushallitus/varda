import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

@Component({
    selector: 'app-ei-henkilostoa-dialog',
    templateUrl: './ei-henkilostoa-dialog.component.html',
    styleUrls: ['./ei-henkilostoa-dialog.component.css'],
    standalone: false
})
export class EiHenkilostoaDialogComponent {
  i18n = VirkailijaTranslations;

  constructor(
    private dialogRef: MatDialogRef<EiHenkilostoaDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any) { }

  closeDialog() {
    this.dialogRef.close();
  }
}
