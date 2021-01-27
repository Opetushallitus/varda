import { Component, Input, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { LapsiDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/lapsi-dto';
import { VarhaiskasvatuspaatosDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/varhaiskasvatuspaatos-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { KoodistoEnum } from 'varda-shared';
import { VarhaiskasvatustiedotContactDialogComponent } from '../../../utility-components/contact-dialog/varhaiskasvatustiedot-contact-dialog/varhaiskasvatustiedot-contact-dialog.component';

@Component({
  selector: 'app-varhaiskasvatuspaatos',
  templateUrl: './varhaiskasvatuspaatos.component.html',
  styleUrls: ['./varhaiskasvatuspaatos.component.css']
})
export class VarhaiskasvatuspaatosComponent implements OnInit {
  @Input() lapsi: LapsiDTO;
  @Input() vakapaatos: VarhaiskasvatuspaatosDTO;
  @Input() oma_organisaatio_sahkoposti: string;
  i18n = HuoltajaTranslations;
  koodistoEnum = KoodistoEnum;
  toimipaikkaList: Array<string> = [];
  isKunnallinen = false;


  constructor(private dialog: MatDialog) { }

  ngOnInit() {
    this.isKunnallinen = ['jm01', 'jm02', 'jm03'].includes(this.vakapaatos.jarjestamismuoto_koodi.toLocaleLowerCase());

    this.toimipaikkaList = this.vakapaatos.varhaiskasvatussuhteet.map(vakasuhde => vakasuhde.toimipaikka.toimipaikka_nimi)
      .filter((toimipaikka, index, arr) => arr.lastIndexOf(toimipaikka) === index)
      .sort((a, b) => a.localeCompare(b));

    this.sortVarhaiskasvatussuhteet();
  }

  togglePanel(panel: any) {
    panel.toggle_expanded = !panel.toggle_expanded;
  }

  openDialog(lapsi?: LapsiDTO) {
    this.dialog.open(VarhaiskasvatustiedotContactDialogComponent, {
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
