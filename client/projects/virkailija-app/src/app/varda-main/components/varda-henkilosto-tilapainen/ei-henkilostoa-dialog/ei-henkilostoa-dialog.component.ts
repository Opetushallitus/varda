import { Component, OnInit, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-ei-henkilostoa-dialog',
  templateUrl: './ei-henkilostoa-dialog.component.html',
  styleUrls: ['./ei-henkilostoa-dialog.component.css']
})
export class EiHenkilostoaDialogComponent implements OnInit {

  constructor(
    private dialogRef: MatDialogRef<EiHenkilostoaDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any) { }

  ngOnInit(): void {
  }

  closeDialog() {
    this.dialogRef.close();
  }
}
