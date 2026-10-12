import { Component, Input, OnDestroy } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { HuoltajaApiService } from 'projects/huoltaja-app/src/app/services/huoltaja-api.service';
import { VarhaiskasvatustiedotDTO, LapsiDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/lapsi-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { Subscription } from 'rxjs';
import { ContactDialogComponent } from '../../utility-components/contact-dialog/contact-dialog.component';


@Component({
    selector: 'app-varhaiskasvatustiedot',
    templateUrl: './varhaiskasvatustiedot.component.html',
    styleUrls: ['./varhaiskasvatustiedot.component.css'],
    standalone: false
})
export class VarhaiskasvatustiedotComponent implements OnDestroy {
  @Input() henkilo_oid: string;
  i18n = HuoltajaTranslations;
  varhaiskasvatustiedot: VarhaiskasvatustiedotDTO;
  subscriptions: Array<Subscription> = [];

  constructor(
    private huoltajaApiService: HuoltajaApiService,
    private dialog: MatDialog
  ) {
    this.subscriptions.push(
      this.huoltajaApiService.getVarhaiskasvatustiedot().subscribe((varhaiskasvatustiedot: VarhaiskasvatustiedotDTO) => {
        this.varhaiskasvatustiedot = this.sortVakapaatokset({ ...varhaiskasvatustiedot });
      })
    );
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  openDialog(title: string, content: string) {
    this.dialog.open(ContactDialogComponent, { data: { title, content }, autoFocus: false });
  }

  sortVakapaatokset(varhaiskasvatustiedot: VarhaiskasvatustiedotDTO) {
    if (!varhaiskasvatustiedot?.lapset) {
      return null;
    }

    const lapsetOneByOne: Array<LapsiDTO> = [];
    varhaiskasvatustiedot.lapset?.forEach(lapsi => {
      lapsi?.varhaiskasvatuspaatokset?.forEach(vakapaatos => {
        const lapsiByPaatos: LapsiDTO = { ...lapsi, varhaiskasvatuspaatos: vakapaatos, varhaiskasvatuspaatokset: null };
        lapsetOneByOne.push(lapsiByPaatos);
      });
    });

    lapsetOneByOne.sort((a, b) => {
      const sortA = a.varhaiskasvatuspaatos;
      const sortB = b.varhaiskasvatuspaatos;

      const sortByA = sortA.paattymis_pvm ? `${sortA.alkamis_pvm}x${sortA.paattymis_pvm}` : `x${sortA.alkamis_pvm}`;
      const sortByB = sortB.paattymis_pvm ? `${sortB.alkamis_pvm}x${sortB.paattymis_pvm}` : `x${sortB.alkamis_pvm}`;
      return sortByB.localeCompare(sortByA);
    });


    varhaiskasvatustiedot.lapset = lapsetOneByOne;
    return varhaiskasvatustiedot;
  }
}
