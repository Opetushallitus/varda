import { Component, OnInit, OnChanges, Input, Output, ViewChildren, EventEmitter, QueryList } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { TyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tyontekija-dto.model';
import { VardaPoissaoloDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-poissolo-dto.model';
import { VardaTyontekijaTaydennyskoulutusComponent } from './varda-tyontekija-taydennyskoulutus/varda-tyontekija-taydennyskoulutus.component';
import { KoodistoDTO, KoodistoEnum } from 'projects/varda-shared/src/lib/dto/koodisto-models';
import { VardaKoodistoService } from 'varda-shared';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { forkJoin } from 'rxjs';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';

@Component({
  selector: 'app-varda-tyontekija-taydennyskoulutukset',
  templateUrl: './varda-tyontekija-taydennyskoulutukset.component.html',
  styleUrls: ['./varda-tyontekija-taydennyskoulutukset.component.css', '../varda-tyontekija-form.component.css']
})
export class VardaTyontekijaTaydennyskoulutuksetComponent implements OnInit, OnChanges {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() tyontekija: TyontekijaListDTO;
  @ViewChildren(VardaTyontekijaTaydennyskoulutusComponent) taydennyskoulutusElements: QueryList<VardaTyontekijaTaydennyskoulutusComponent>;
  i18n = VirkailijaTranslations;
  expandPanel = false;
  taydennyskoulutukset: Array<VardaPoissaoloDTO>;
  tehtavanimikkeet: KoodistoDTO;
  addTaydennyskoulutus: boolean;

  constructor(
    private koodistoService: VardaKoodistoService,
    private henkilostoService: VardaHenkilostoApiService,
    private vakajarjestajaService: VardaVakajarjestajaService,
  ) { }

  ngOnInit() {
    if (this.toimipaikkaAccess.taydennyskoulutustiedot.katselija) {
      this.getTaydennyskoulutukset();
      this.setTehtavanimikkeet();
    } else {
      this.taydennyskoulutukset = [];
    }

    this.expandPanel = this.toimipaikkaAccess.taydennyskoulutustiedot.katselija && !this.toimipaikkaAccess.tyontekijatiedot.katselija;
  }

  ngOnChanges() { }

  togglePanel(open: boolean) {
    this.expandPanel = open;
  }

  setTehtavanimikkeet() {
    const searchParams = { vakajarjestaja_oid: this.vakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid, henkilo_oid: this.tyontekija.henkilo_oid };
    forkJoin([
      this.koodistoService.getKoodisto(KoodistoEnum.tehtavanimike),
      this.henkilostoService.getTaydennyskoulutuksetTyontekijat(searchParams)
    ]).subscribe(([koodisto, henkiloNimikkeet]) => {
      henkiloNimikkeet = henkiloNimikkeet.filter(henkilo => henkilo.henkilo_oid === this.tyontekija.henkilo_oid);
      this.tehtavanimikkeet = koodisto;
      this.tehtavanimikkeet.codes = koodisto.codes.filter(code => henkiloNimikkeet.find(henkilo => henkilo.tehtavanimike_koodit?.includes(code.code_value)));
    });
  }

  getTaydennyskoulutukset() {

    this.taydennyskoulutukset = null;
    const searchParams = { henkilo_oid: this.tyontekija.henkilo_oid };
    this.henkilostoService.getTaydennyskoulutukset(searchParams).subscribe({
      next: taydennyskoulutusData => this.taydennyskoulutukset = taydennyskoulutusData,
      error: err => console.error(err)
    });
  }

  initTaydennyskoulutus() {
    this.addTaydennyskoulutus = true;
    this.setTehtavanimikkeet();
    setTimeout(() => this.togglePanel(true), 0);
    setTimeout(() => this.taydennyskoulutusElements.last.element.nativeElement.scrollIntoView({ behavior: 'smooth' }), 100);
  }

  closeAddTaydennyskoulutus(refreshSuhteet?: boolean) {
    this.addTaydennyskoulutus = false;
    if (refreshSuhteet) {
      this.getTaydennyskoulutukset();
    }
  }
}
