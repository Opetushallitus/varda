import {Component, OnInit, Input, OnChanges, SimpleChanges, SimpleChange, ViewChild, ElementRef, Output, EventEmitter} from '@angular/core';

// Since we are using native bootstrap instead of angular one we need this to access the modal
declare var $: any;

export enum ModalEvent {
  opens = 'opens',
  hides = 'hides',
  hidden = 'hidden',
}

@Component({
  selector: 'app-varda-modal-form',
  templateUrl: './varda-modal-form.component.html',
  styleUrls: ['./varda-modal-form.component.css']
})
export class VardaModalFormComponent implements OnInit, OnChanges {

  @Input() identifier: string;
  @Input() modalTitle: string;
  @Input() isLg: boolean;
  @Input() isXl: boolean;
  @Input() openModal: boolean;
  @Input() closeWithoutConfirm: boolean;

  confirmedVardaFormLeave: boolean;
  showPrompt: boolean;

  @Output() events: EventEmitter<ModalEvent> = new EventEmitter(true);

  @ViewChild('vardamodal', { static: true }) vardaModal: ElementRef;
  @ViewChild('vardaPromptModal') vardaModalPrompt: ElementRef;

  constructor() {
    this.confirmedVardaFormLeave = false;
    this.showPrompt = false;
  }

  ngOnInit(): void {
    const modalElement = this.vardaModal.nativeElement;
    // Event when modal is visible to user
    $(modalElement).on('shown.bs.modal', (e) => {
      this.events.emit(ModalEvent.opens);
    });
    // Event when hide has been called
    $(modalElement).on('hide.bs.modal', (e) => {
      this.events.emit(ModalEvent.hides);
      if (!this.closeWithoutConfirm && !this.confirmedVardaFormLeave) {
        this.showPrompt = true;
        return e.preventDefault();
      }
    });
    // Event just before modal hides
    $(modalElement).on('hidden.bs.modal', (e) => {
      this.events.emit(ModalEvent.hidden);
      this.confirmedVardaFormLeave = false;
      this.showPrompt = false;
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    const openModal: SimpleChange = changes.openModal;
    if (openModal) {
      openModal.currentValue === true ? this.showModal() : this.hideModal();
    }
  }

  private showModal() {
    const modalElement = this.vardaModal.nativeElement;
    // Open modal
    $(modalElement).modal('show');
  }

  private hideModal() {
    const modalElement = this.vardaModal.nativeElement;
    $(modalElement).modal('hide');
  }

  moveToCancel(e: Event): void {
    setTimeout(() => {
      $('#vardaPromptModalStay').focus();
    });
  }

  moveToLeave(e: Event): void {
    setTimeout(() => {
      $('#vardaPromptModalLeave').focus();
    });
  }

  stayOnForm(): void {
    this.showPrompt = false;
    $(this.vardaModal.nativeElement).attr('tabindex', -1);
  }

  leaveFormByPrompt(): void {
    this.confirmedVardaFormLeave = true;
    this.hideModal();
  }

}
