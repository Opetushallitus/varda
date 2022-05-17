import { Component, OnInit, Input, ViewChildren, QueryList } from '@angular/core';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaPalvelussuhdeComponent } from './varda-palvelussuhde/varda-palvelussuhde.component';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VardaFormListAbstractComponent } from '../../varda-form-list-abstract.component';
import { TyontekijaPalvelussuhde } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { sortByAlkamisPvm } from '../../../../../utilities/helper-functions';

@Component({
  selector: 'app-varda-palvelussuhteet',
  templateUrl: './varda-palvelussuhteet.component.html',
  styleUrls: [
    './varda-palvelussuhteet.component.css',
    '../varda-tyontekija-form.component.css',
    '../../varda-henkilo-form.component.css'
  ]
})
export class VardaPalvelussuhteetComponent extends VardaFormListAbstractComponent<TyontekijaPalvelussuhde> implements OnInit {
  @ViewChildren(VardaPalvelussuhdeComponent) objectElements: QueryList<VardaPalvelussuhdeComponent>;
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;

  constructor(private henkilostoService: VardaHenkilostoApiService) {
    super();
  }

  ngOnInit() {
    this.objectList = this.henkilostoService.activeTyontekija.getValue().palvelussuhteet.sort(sortByAlkamisPvm);
  }

  updateActiveObject() {
    const activeTyontekija = this.henkilostoService.activeTyontekija.getValue();
    this.henkilostoService.activeTyontekija.next({...activeTyontekija, palvelussuhteet: this.objectList});
  }
}
