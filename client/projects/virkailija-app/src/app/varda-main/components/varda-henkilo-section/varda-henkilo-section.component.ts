import {Component, Input, OnChanges, OnInit, SimpleChanges} from '@angular/core';
import {VardaHenkiloService} from '../../services/varda-henkilo.service';
import {VardaModalService} from '../../../core/services/varda-modal.service';
import {VardaExtendedHenkiloModel, VardaHenkiloSearchConfiguration} from '../../../utilities/models';
import {TranslateService} from '@ngx-translate/core';

@Component({
  selector: 'app-varda-henkilo-section',
  templateUrl: './varda-henkilo-section.component.html',
  styleUrls: ['./varda-henkilo-section.component.css']
})
export class VardaHenkiloSectionComponent implements OnInit, OnChanges {

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
