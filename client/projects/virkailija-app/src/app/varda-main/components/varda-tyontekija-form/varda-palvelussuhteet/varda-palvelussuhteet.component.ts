import { Component, OnInit, OnChanges, Input, Output, ViewChildren, QueryList, SimpleChanges } from '@angular/core';
import { VardaToimipaikkaDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaPalvelussuhdeDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-palvelussuhde-dto.model';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { VardaPalvelussuhdeComponent } from './varda-palvelussuhde/varda-palvelussuhde.component';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-varda-palvelussuhteet',
  templateUrl: './varda-palvelussuhteet.component.html',
  styleUrls: ['./varda-palvelussuhteet.component.css', '../varda-tyontekija-form.component.css']
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
    private henkilostoService: VardaHenkilostoApiService
  ) {

  }


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
      error: err => console.error(err)
    });
  }

  initPalvelussuhde() {
    this.addPalvelussuhdeBoolean = true;
    setTimeout(() => this.togglePanel(true), 0);
    setTimeout(() => this.palvelussuhdeElements.last.element.nativeElement.scrollIntoView({ behavior: 'smooth' }), 100);
  }

  closeAddPalvelussuhde(refreshSuhteet?: boolean) {
    this.addPalvelussuhdeBoolean = false;
    if (refreshSuhteet) {
      this.getPalvelussuhteet();
    }
  }
}
