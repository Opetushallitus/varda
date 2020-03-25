import { Component, OnInit, Input, Output, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
import { VardaHenkiloService } from '../../services/varda-henkilo.service';
import { VardaModalService } from '../../../core/services/varda-modal.service';
import {
  VardaHenkiloDTO,
  VardaHenkiloSearchConfiguration,
  VardaExtendedHenkiloModel
} from '../../../utilities/models';
import { ModalEvent } from '../../../shared/components/varda-modal-form/varda-modal-form.component';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { map } from 'rxjs/operators';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-varda-henkilo-list',
  templateUrl: './varda-henkilo-list.component.html',
  styleUrls: ['./varda-henkilo-list.component.css']
})
export class VardaHenkiloListComponent implements OnInit, OnChanges {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkiloList: Array<VardaExtendedHenkiloModel>;
  @Input() henkiloSearchValue: VardaHenkiloSearchConfiguration;
  @Output() henkiloListUpdated: EventEmitter<any> = new EventEmitter<any>();

  henkilot: Array<VardaExtendedHenkiloModel> = [];
  activeHenkiloItemId: string;
  activeHenkiloItem: VardaHenkiloDTO;
  previousSearchValue: string;
  ui: {
    isLoading: boolean
  };
  henkiloFormOpen: boolean;
  searchTimeout: any;
  showHenkiloCountText: boolean;
  confirmedHenkiloFormLeave: boolean;
  paosKatselijaObservable: Observable<boolean>;

  constructor(private vardaHenkiloService: VardaHenkiloService,
    private vardaModalService: VardaModalService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService) {
    this.ui = {
      isLoading: false
    };
    this.henkiloFormOpen = false;
    this.showHenkiloCountText = true;
    this.confirmedHenkiloFormLeave = true;

    this.vardaModalService.modalOpenObs('henkiloForm').subscribe((data) => {
      if (data.data['isNew']) {
        this.activeHenkiloItem = null;
      }
      this.openHenkiloForm();
    });

    this.paosKatselijaObservable = this.vardaVakajarjestajaService.getSelectedToimipaikkaObs()
      .pipe(map(toimipaikka => {
        if (toimipaikka.paos_toimipaikka_kytkin) {
          const toimipaikkaTallentajaIdList = toimipaikka.paos_tallentaja_organisaatio_id_list;
          return toimipaikkaTallentajaIdList &&
            !toimipaikkaTallentajaIdList.includes(parseInt(this.vardaVakajarjestajaService.selectedVakajarjestaja.id));
        } else {
          return false;
        }
      }));
  }

  addHenkilo(): void {
    this.vardaModalService.openModal('henkiloForm', true, { isNew: true });
  }

  editHenkilo(data: any): void {
    this.activeHenkiloItem = data;
    this.openHenkiloForm();
  }

  onLapsiUpdated(data: any): void {
    if (data.saveVarhaiskasvatuspaatos) {
      const henkiloToUpdate = this.henkiloList.find((henkiloItem) => {
        const lapsi = henkiloItem.lapsi;
        return lapsi.url === data.saveVarhaiskasvatuspaatos.url;
      });

      const lapsiObj = henkiloToUpdate.lapsi;
      if (lapsiObj) {
        lapsiObj['varhaiskasvatuspaatokset_top'].push(data.saveVarhaiskasvatuspaatos.entity);
      }
    }
  }

  onLapsiDeleted(data: any): void {
    const lapsiToDeleteIndex = this.henkiloList.findIndex((henkiloItem) => {
      const lapsi = henkiloItem.lapsi;
      return lapsi.url === data;
    });

    if (lapsiToDeleteIndex !== -1) {
      this.henkiloList.splice(lapsiToDeleteIndex, 1);
    }

    this.searchHenkilo(this.henkiloSearchValue);
  }

  onHenkiloAdded(extendedHenkilo: VardaExtendedHenkiloModel): void {
    this.confirmedHenkiloFormLeave = true;
    this.henkiloFormOpen = false;
    extendedHenkilo.isNew = true;
    this.henkiloList.push(extendedHenkilo);
    this.activeHenkiloItem = extendedHenkilo.henkilo;
    this.activeHenkiloItemId = extendedHenkilo.henkilo.url;
    this.searchHenkilo(this.henkiloSearchValue);
  }

  openHenkiloForm(): void {
    this.ui.isLoading = true;
    this.henkiloFormOpen = true;
    this.ui.isLoading = false;
  }

  henkiloFormValuesChanged(hasChanged: boolean): void {
    this.confirmedHenkiloFormLeave = !hasChanged;
  }

  searchHenkilo(searchObj: VardaHenkiloSearchConfiguration): void {
    const searchValue = searchObj.searchValue;

    this.showHenkiloCountText = true;

    if (!searchObj.displayAll) {
      this.showHenkiloCountText = false;
    }

    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }

    this.previousSearchValue = searchValue;

    const cloneHenkiloList = Object.assign(this.henkiloList);

    this.searchTimeout = setTimeout(() => {
      this.henkilot = this.vardaHenkiloService.searchByStrAndEntityFilter(searchObj, cloneHenkiloList);
      this.henkiloListUpdated.emit(this.henkilot);
    });
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.henkiloSearchValue && changes.henkiloSearchValue.currentValue) {
      const searchObj = changes.henkiloSearchValue.currentValue;
      this.searchHenkilo(searchObj);
    }

    if (changes.henkiloList) {
      this.henkilot = Object.assign(this.henkiloList);
      this.searchHenkilo(this.henkiloSearchValue);
    }
  }

  ngOnInit() {
    this.henkilot = Object.assign(this.henkiloList);
  }

  handleFormClose($event: ModalEvent) {
    if ($event === ModalEvent.hidden) {
      this.henkiloFormOpen = false;
      this.confirmedHenkiloFormLeave = true;
    }
  }
}
