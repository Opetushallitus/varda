import {
  Component,
  Input,
  OnChanges,
  SimpleChanges,
  ElementRef,
  AfterViewInit,
  Output,
  EventEmitter,
  ViewChild,
  OnDestroy
} from '@angular/core';
import { Modal } from 'bootstrap';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';

export enum ModalEvent {
  opens = 'opens',
  hides = 'hides',
  hidden = 'hidden',
}

@Component({
    selector: 'app-varda-modal-form',
    templateUrl: './varda-modal-form.component.html',
    styleUrls: ['./varda-modal-form.component.css'],
    standalone: false
})
export class VardaModalFormComponent implements OnChanges, OnDestroy, AfterViewInit {
  @Input() identifier: string;
  @Input() modalTitle: string;
  @Input() isLg: boolean;
  @Input() isXl: boolean;
  @Input() openModal: boolean;
  @Input() closeWithoutConfirm: boolean;
  @Output() events: EventEmitter<ModalEvent> = new EventEmitter(true);

  @ViewChild('vardamodal', { static: false }) vardaModal: ElementRef;
  @ViewChild('vardaPromptModalStay') vardaPromptModalStay: ElementRef;
  @ViewChild('vardaPromptModalLeave') vardaPromptModalLeave: ElementRef;
  @ViewChild('modalBackdrop') modalBackdrop: ElementRef;

  confirmedVardaFormLeave: boolean = false;
  showPrompt: boolean = false;
  i18n = VirkailijaTranslations;

  private modalInstance!: Modal;
  private cleanup: (() => void)[] = [];

  ngAfterViewInit() {
    this.modalInstance = new Modal(this.vardaModal.nativeElement);

    this.vardaModal.nativeElement.addEventListener('hide.bs.modal', (event: Event) => {
      this.events.emit(ModalEvent.hides);
      if (!this.closeWithoutConfirm && !this.confirmedVardaFormLeave) {
        this.showPrompt = true;
        event.preventDefault();
      } else {
        this.hideModal();
      }
    });

    this.vardaModal.nativeElement.addEventListener('hidden.bs.modal', () => {
      this.events.emit(ModalEvent.hidden);
      this.confirmedVardaFormLeave = false;
      this.showPrompt = false;
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.openModal?.currentValue === true) {
      this.showModal();
    } else if (changes.openModal?.currentValue === false) {
      this.hideModal();
    }
  }

  ngOnDestroy(): void {
    this.cleanup.forEach(fn => fn());
  }

  moveToCancel(): void {
    setTimeout(() => {
      this.vardaPromptModalStay?.nativeElement.focus();
    });
  }

  moveToLeave(): void {
    setTimeout(() => {
      this.vardaPromptModalLeave?.nativeElement.focus();
    });
  }

  stayOnForm(): void {
    this.showPrompt = false;
    this.vardaModal.nativeElement.focus();
  }

  leaveFormByPrompt(): void {
    this.confirmedVardaFormLeave = true;
    this.hideModal();
  }

  private showModal(): void {
    setTimeout(() => {
      this.events.emit(ModalEvent.opens);
      this.modalInstance.show();
    });
  }

  private hideModal(): void {
    this.showPrompt = false;
    this.confirmedVardaFormLeave = false;
    setTimeout(() => {
      this.events.emit(ModalEvent.hidden);
      this.modalInstance.hide();
    });
  }
}
