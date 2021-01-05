import { Component, OnInit, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';

@Component({
  selector: 'app-contact-dialog',
  templateUrl: './contact-dialog.component.html',
  styleUrls: ['./contact-dialog.component.css']
})
export class ContactDialogComponent implements OnInit {
  i18n = HuoltajaTranslations;

  constructor(
    private dialogRef: MatDialogRef<ContactDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any) { }

  ngOnInit(): void {
  }

  closeDialog() {
    this.dialogRef.close();
  }
}
