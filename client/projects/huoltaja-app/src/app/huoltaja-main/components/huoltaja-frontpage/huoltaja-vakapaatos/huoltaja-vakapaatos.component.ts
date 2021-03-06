import { Component, Input, OnInit } from '@angular/core';
import { VarhaiskasvatuspaatosDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/varhaiskasvatuspaatos-dto';
import { ContactDialogComponent } from '../../contact-dialog/contact-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { LapsiDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/lapsi-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';

@Component({
  selector: 'app-huoltaja-vakapaatos',
  templateUrl: './huoltaja-vakapaatos.component.html',
  styleUrls: ['../huoltaja-frontpage.component.css', './huoltaja-vakapaatos.component.css']
})
export class HuoltajaFrontpageVakapaatosComponent implements OnInit {
  @Input() lapsi: LapsiDTO;
  @Input() vakapaatos: VarhaiskasvatuspaatosDTO;
  @Input() oma_organisaatio_sahkoposti: string;
  voimassa: boolean;
  toimipaikkaList: Array<string> = [];
  translation = HuoltajaTranslations;

  constructor(private dialog: MatDialog) {
  }

  ngOnInit() {
    this.voimassa = this.isOngoing(this.vakapaatos.paattymis_pvm);
    this.toimipaikkaList = this.vakapaatos.varhaiskasvatussuhteet.map(vakasuhde => vakasuhde.toimipaikka.toimipaikka_nimi)
      .filter((toimipaikka, index, arr) => arr.lastIndexOf(toimipaikka) === index)
      .sort((a, b) => a.localeCompare(b));

    this.sortVarhaiskasvatussuhteet();
  }

  togglePanel(panel: any) {
    panel.toggle_expanded = !panel.toggle_expanded;
  }

  isOngoing(date: string): boolean {
    const today = new Date();
    return !(date < today.toISOString());
  }

  openDialog(lapsi?: LapsiDTO) {
    this.dialog.open(ContactDialogComponent, {
      data: {
        email: lapsi?.yhteysosoite,
        toimija: lapsi?.varhaiskasvatuksen_jarjestaja,
        lakkautettu: lapsi?.aktiivinen_toimija === false
      }
    });
  }

  sortVarhaiskasvatussuhteet() {
    this.vakapaatos.varhaiskasvatussuhteet.sort((a, b) => b.alkamis_pvm.localeCompare(a.alkamis_pvm));
    this.vakapaatos.varhaiskasvatussuhteet.sort((a, b) => {
      const sortByA = a.paattymis_pvm ? `${a.alkamis_pvm}x${a.paattymis_pvm}` : `x${a.alkamis_pvm}`;
      const sortByB = b.paattymis_pvm ? `${b.alkamis_pvm}x${b.paattymis_pvm}` : `x${b.alkamis_pvm}`;
      return sortByB.localeCompare(sortByA);
    });
  }
}
