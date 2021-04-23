import { Component, OnInit, Input, ViewChildren, QueryList } from '@angular/core';
import { VardaToimipaikkaDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaPalvelussuhdeDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-palvelussuhde-dto.model';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { VardaPalvelussuhdeComponent } from './varda-palvelussuhde/varda-palvelussuhde.component';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';

@Component({
  selector: 'app-varda-palvelussuhteet',
  templateUrl: './varda-palvelussuhteet.component.html',
  styleUrls: [
    './varda-palvelussuhteet.component.css',
    '../varda-tyontekija-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaPalvelussuhteetComponent implements OnInit {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() tyontekija: TyontekijaListDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Input() henkilonTutkinnot: Array<VardaTutkintoDTO>;
  @ViewChildren(VardaPalvelussuhdeComponent) palvelussuhdeElements: QueryList<VardaPalvelussuhdeComponent>;
  i18n = VirkailijaTranslations;
  expandPanel = true;
  currentToimipaikka: VardaToimipaikkaDTO;
  palvelussuhteet: Array<VardaPalvelussuhdeDTO>;
  addPalvelussuhdeBoolean: boolean;

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private snackBarService: VardaSnackBarService,
  ) { }

  ngOnInit() {
    if (this.toimipaikkaAccess.tyontekijatiedot.katselija) {
      this.getPalvelussuhteet();
    } else {
      this.palvelussuhteet = [];
    }
  }

  togglePanel(open: boolean) {
    this.expandPanel = open;
  }

  getPalvelussuhteet() {
    this.palvelussuhteet = null;

    this.henkilostoService.getPalvelussuhteet(this.tyontekija.id).subscribe({
      next: palvelussuhdeData => this.palvelussuhteet = palvelussuhdeData,
      error: err => this.snackBarService.errorWithConsole(this.i18n.palvelussuhteet_fetch_failure, err)
    });
  }

  initPalvelussuhde() {
    this.addPalvelussuhdeBoolean = true;
    setTimeout(() => this.togglePanel(true), 0);
    setTimeout(() => this.palvelussuhdeElements.last.element.nativeElement.scrollIntoView({ behavior: 'smooth' }), 100);
  }

  closePalvelussuhde(refreshSuhteet?: boolean, hideAddPalvelussuhde?: boolean) {
    if (hideAddPalvelussuhde) {
      this.addPalvelussuhdeBoolean = false;
    }

    if (refreshSuhteet) {
      this.getPalvelussuhteet();
    }
  }
}
