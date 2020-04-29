import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { HenkilohakuSearchDTO, HenkilohakuType, FilterStatus, FilterObject } from '../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { FormControl, FormGroup } from '@angular/forms';
import { Subscription, Observable } from 'rxjs';
import { HakuAccess } from '../varda-haku-container.component';
import { LoadingHttpService } from 'varda-shared';
import { delay } from 'rxjs/internal/operators/delay';

@Component({
  selector: 'app-haku-condition',
  templateUrl: './haku-condition.component.html',
  styleUrls: ['./haku-condition.component.css']
})
export class HakuConditionComponent implements OnInit, OnDestroy {
  @Input() searchAction: (action) => void;
  @Input() access: HakuAccess;
  hakuform: FormGroup;
  typeformSubsciption: Subscription;
  filterStatusFormSubsciption: Subscription;
  filterObjectFormSubsciption: Subscription;

  HenkilohakuType: typeof HenkilohakuType = HenkilohakuType;
  FilterStatus: typeof FilterStatus = FilterStatus;
  FilterObject: typeof FilterObject = FilterObject;

  searchData: HenkilohakuSearchDTO;
  isLoading: Observable<boolean>;

  constructor(private loadingHttpService: LoadingHttpService) {
    this.isLoading = loadingHttpService.isLoading().pipe(delay(200));
  }

  ngOnInit() {
    this.searchData = new HenkilohakuSearchDTO();
    const typeForm = new FormControl('');
    const searchForm = new FormControl('');
    const filterStatusForm = new FormControl(FilterStatus.voimassaOlevat);
    const filterObjectForm = new FormControl('');
    this.hakuform = new FormGroup({ type: typeForm, search: searchForm, filter_status: filterStatusForm, filter_object: filterObjectForm });
    this.typeformSubsciption = typeForm.valueChanges
      .subscribe(((typeValue) => this.searchType(typeValue)));
    this.filterStatusFormSubsciption = filterStatusForm.valueChanges
      .subscribe(((filterStatus) => this.searchFilterStatus(filterStatus)));
    this.filterObjectFormSubsciption = filterObjectForm.valueChanges
      .subscribe(((filterObject) => this.searchFilterObject(filterObject)));
  }

  ngOnDestroy() {
    this.typeformSubsciption.unsubscribe();
    this.filterStatusFormSubsciption.unsubscribe();
    this.filterObjectFormSubsciption.unsubscribe();
  }

  searchType(typeValue?: HenkilohakuType) {
    const searchDto = this.hakuform.value;
    if (typeValue) {
      searchDto.type = typeValue;
    }
    this.searchAction(searchDto);
  }

  searchFilterStatus(status?: FilterStatus) {
    if (this.hakuform.controls.filter_status.value === FilterStatus.eiMaksutietoja) {
      this.hakuform.value.filter_object = FilterObject.maksutiedot;
    } else {
      if (this.hakuform.controls.filter_object.value === FilterObject.maksutiedot) {
        this.hakuform.value.filter_object = '';
      }
    }

    const searchDto = this.hakuform.value;
    if (status) {
      searchDto.filter_status = status;
    }
    this.searchAction(searchDto);
  }

  searchFilterObject(object?: FilterObject) {
    const searchDto = this.hakuform.value;
    if (object) {
      searchDto.filter_object = object;
    }
    this.searchAction(searchDto);
  }
}
