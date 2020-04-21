import { TranslateService } from '@ngx-translate/core';
import { Component, OnInit, OnChanges, Input, SimpleChanges } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaExtendedHenkiloModel, VardaHenkiloSearchConfiguration } from 'projects/virkailija-app/src/app/utilities/models';
import { VardaModalService } from 'projects/virkailija-app/src/app/core/services/varda-modal.service';
import { VardaHenkiloService } from '../../../services/varda-henkilo.service';

@Component({
  selector: 'app-varda-lapsi-section',
  templateUrl: './varda-lapsi-section.component.html',
  styleUrls: ['./varda-lapsi-section.component.css']
})
export class VardaLapsiSectionComponent implements OnInit, OnChanges {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilot: Array<VardaExtendedHenkiloModel>;

  showLapset: boolean;
  showTyontekijat: boolean;
  activeFilter: string;
  currentSearchValue: string;
  henkiloFormOpen: boolean;
  henkiloSearchObj: VardaHenkiloSearchConfiguration;
  henkiloList: Array<VardaExtendedHenkiloModel>;

  constructor(
    private vardaModalService: VardaModalService,
    private vardaHenkiloService: VardaHenkiloService,
    private translateService: TranslateService) {
    this.showLapset = true;
    this.showTyontekijat = true;
    this.activeFilter = 'lapsi';
    this.currentSearchValue = '';
    this.henkiloFormOpen = false;
  }

  getPlaceholderText(): string {
    let rv = '';
    this.translateService.get('placeholder.who-are-you-looking-for').subscribe((translation) => {
      rv = translation;
    });
    return rv;
  }

  searchValueChanged(event: any): void {
    this.currentSearchValue = event.target.value;
    this.henkiloSearchObj = this.vardaHenkiloService.createHenkiloSearchObj(this.activeFilter, this.currentSearchValue);
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.henkilot && changes.henkilot.currentValue) {
      this.henkiloList = changes.henkilot.currentValue;

      if (this.henkiloList.length <= 10) {
        this.currentSearchValue = '';
      }

      this.henkiloSearchObj = this.vardaHenkiloService.createHenkiloSearchObj(this.activeFilter, this.currentSearchValue);
    }
  }

  ngOnInit() {
    this.vardaModalService.modalOpenObs('henkiloForm').subscribe((isOpen: boolean) => {
      this.henkiloFormOpen = isOpen;
    });
    this.henkiloSearchObj = this.vardaHenkiloService.createHenkiloSearchObj(this.activeFilter, this.currentSearchValue);
    this.henkiloList = [];
  }

}
