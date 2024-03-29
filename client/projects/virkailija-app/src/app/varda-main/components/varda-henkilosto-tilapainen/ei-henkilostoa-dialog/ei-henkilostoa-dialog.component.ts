import { Component, OnInit, Inject } from '@angular/core';
import { MAT_LEGACY_DIALOG_DATA as MAT_DIALOG_DATA, MatLegacyDialogRef as MatDialogRef } from '@angular/material/legacy-dialog';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-ei-henkilostoa-dialog',
  templateUrl: './ei-henkilostoa-dialog.component.html',
  styleUrls: ['./ei-henkilostoa-dialog.component.css']
})
export class EiHenkilostoaDialogComponent implements OnInit {
  i18n = VirkailijaTranslations;

  constructor(
    private dialogRef: MatDialogRef<EiHenkilostoaDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any) { }

  ngOnInit(): void {
  }

  closeDialog() {
    this.dialogRef.close();
  }
}
