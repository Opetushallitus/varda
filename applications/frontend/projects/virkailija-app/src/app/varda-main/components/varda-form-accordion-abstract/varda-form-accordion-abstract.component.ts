import {
  Component,
  Output,
  ViewChild,
  EventEmitter,
  ElementRef,
  OnDestroy,
  OnInit,
  Input
} from '@angular/core';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { VardaLapsiService } from 'projects/virkailija-app/src/app/core/services/varda-lapsi.service';
import { PuutteellinenErrorDTO } from '../../../utilities/models/dto/varda-puutteellinen-dto.model';
import { VardaVakajarjestajaApiService } from '../../../core/services/varda-vakajarjestaja-api.service';
import { MatExpansionPanel, MatExpansionPanelHeader } from '@angular/material/expansion';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';
import { FormGroup } from '@angular/forms';
import { VardaModalService } from '../../../core/services/varda-modal.service';
import { Subscription } from 'rxjs';
import { ModelNameEnum } from '../../../utilities/models/enums/model-name.enum';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';
import { distinctUntilChanged, filter } from 'rxjs/operators';

@Component({
    template: '',
    standalone: false
})
export abstract class VardaFormAccordionAbstractComponent<T extends {id?: number}> implements OnInit, OnDestroy {
  @ViewChild(MatExpansionPanelHeader) panelHeader: MatExpansionPanelHeader;
  @ViewChild('matPanel', { read: MatExpansionPanel }) matPanel: MatExpansionPanel;
  @ViewChild('matPanel', { read: ElementRef }) matPanelElement: ElementRef;
  @Input() currentObject: T;
  @Output() closeEmitter = new EventEmitter();
  @Output() setBaseObject = new EventEmitter<any>();

  i18n = VirkailijaTranslations;
  formGroup: FormGroup;
  isEdit: boolean;
  isSubmitting = false;
  modelName: ModelNameEnum;

  protected errorList: Array<PuutteellinenErrorDTO>;
  protected subscriptions: Array<Subscription> = [];
  protected apiService: VardaLapsiService | VardaHenkilostoApiService | VardaVakajarjestajaApiService;

  constructor(protected modalService: VardaModalService, protected utilityService: VardaUtilityService) { }

  ngOnInit() {
    this.initForm();

    if (!this.objectExists()) {
      this.togglePanel(true);
      this.enableForm();
      setTimeout(() => this.panelHeader?.focus(), 200);
    } else {
      this.disableForm();
    }

    if (this.currentObject && !this.currentObject.id) {
      // Object is created from a copy so it can be saved immediately
      this.formGroup.markAsDirty();
    }

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true)),
      this.utilityService.getFocusObjectSubject().subscribe(focusObject => {
        if (focusObject?.type === this.modelName && focusObject.id === this.currentObject?.id) {
          this.scrollToPanel();
        }
      })
    );
    this.checkFormErrors();
  }

  checkFormErrors() {
    if (this.objectExists()) {
      this.apiService.getFormErrorList().subscribe(errorList => {
        this.errorList = errorList.filter(error => error.model_name === this.modelName &&
          error.model_id_list.includes(this.currentObject.id));
      });
    }
  }

  togglePanel(open: boolean) {
    setTimeout(() => {
      if (open) {
        this.matPanel?.open();
      } else {
        this.matPanel?.close();
      }
    }, 100);

    if (!open) {
      this.disableForm();
      this.closeEmitter?.emit();
      // Reset fields when accordion is closed
      this.initForm();
    }
  }

  enableForm() {
    this.isEdit = true;

    // https://github.com/angular/angular/issues/22556
    setTimeout(() => {
      this.formGroup.enable();
      this.enableFormExtra();
    });
  }

  /**
   * Use in child components to provide extra enable actions to run inside setTimeout
   */
  enableFormExtra() { }

  disableForm() {
    this.isEdit = false;
    this.modalService.setFormValuesChanged(false);

    // https://github.com/angular/angular/issues/22556
    setTimeout(() => {
      this.formGroup.disable();
      this.disableFormExtra();
    });
  }

  /**
   * Use in child components to provide extra disable actions to run inside setTimeout
   */
  disableFormExtra() { }

  disableSubmit() {
    setTimeout(() => this.isSubmitting = false, 500);
  }

  useAsCopy(event: MouseEvent) {
    event.stopPropagation();
    this.setBaseObject.emit(this.currentObject);
  }

  objectExists() {
    return !!this.currentObject?.id;
  }

  scrollToPanel() {
    setTimeout(() => {
      this.togglePanel(true);
      setTimeout(() => {
        this.matPanelElement?.nativeElement?.scrollIntoView();
        this.panelHeader?.focus();
      }, 200);
    }, 200);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }

  abstract initForm();
}
