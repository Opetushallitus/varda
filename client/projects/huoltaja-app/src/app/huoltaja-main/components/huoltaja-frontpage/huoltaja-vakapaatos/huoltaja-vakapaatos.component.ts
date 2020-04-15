import { Component, Input, OnInit } from '@angular/core';
import { VarhaiskasvatuspaatosDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/varhaiskasvatuspaatos-dto';
import { ContactDialogComponent } from '../../contact-dialog/contact-dialog.component';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-huoltaja-vakapaatos',
  templateUrl: './huoltaja-vakapaatos.component.html',
  styleUrls: ['../huoltaja-frontpage.component.css']
})
export class HuoltajaFrontpageVakapaatosComponent implements OnInit {

  @Input() vakapaatos: VarhaiskasvatuspaatosDTO;
  @Input() oma_organisaatio_sahkoposti: string;
  voimassa: boolean;

  constructor(private dialog: MatDialog) {

  }

  ngOnInit() {
    this.voimassa = this.isOngoing(this.vakapaatos.paattymis_pvm);
  }

  toggleVakapaatos(vakapaatosDto: VarhaiskasvatuspaatosDTO) {
    vakapaatosDto.toggle_expanded = !vakapaatosDto.toggle_expanded;
  }

  isOngoing(date: string): boolean {
    const today = new Date('2019-04-04');
    return !(date < today.toISOString());
  }

  openDialog(email?: string) {
    this.dialog.open(ContactDialogComponent, {
      data: {
        email: email
      }
    });
  }
}
