import { Component, OnDestroy } from '@angular/core';
import { MatLegacyDialog as MatDialog } from '@angular/material/legacy-dialog';
import { HuoltajaApiService } from 'projects/huoltaja-app/src/app/services/huoltaja-api.service';
import { TyontekijatiedotDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/tyontekija-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';
import { Subscription } from 'rxjs';
import { ContactDialogComponent } from '../../utility-components/contact-dialog/contact-dialog.component';

@Component({
  selector: 'app-tyontekijat',
  templateUrl: './tyontekijat.component.html',
  styleUrls: ['./tyontekijat.component.css']
})
export class TyontekijatComponent implements OnDestroy {
  tyontekijatiedot: TyontekijatiedotDTO;
  i18n = HuoltajaTranslations;
  subscriptions: Array<Subscription> = [];
  constructor(
    private huoltajaApiService: HuoltajaApiService,
    private dialog: MatDialog
  ) {
    this.subscriptions.push(
      this.huoltajaApiService.getTyontekijatiedot().subscribe(tyontekijatiedotData => {
        const tyontekijatiedot = { ...tyontekijatiedotData };
        tyontekijatiedot?.tyontekijat?.forEach(tyontekija => {
          this.huoltajaApiService.sortByAlkamisPaattymisPvm(tyontekija?.palvelussuhteet);
          tyontekija.palvelussuhteet.forEach(palvelussuhde => {
            this.huoltajaApiService.sortByAlkamisPaattymisPvm(palvelussuhde.tyoskentelypaikat);
          });
        });

        this.tyontekijatiedot = tyontekijatiedot;
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  openDialog(title: string, content: string) {
    this.dialog.open(ContactDialogComponent, { data: { title, content }, autoFocus: false });
  }
}
