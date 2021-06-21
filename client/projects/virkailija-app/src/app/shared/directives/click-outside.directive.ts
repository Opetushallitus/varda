import { Directive, ElementRef, Input, Output, EventEmitter, HostListener } from '@angular/core';

@Directive({
  selector: '[appClickOutside]'
})
export class ClickOutsideDirective {
  @Output() clickOutside: EventEmitter<any> = new EventEmitter();

  constructor(private elementRef: ElementRef) {}

  @HostListener('document:click', ['$event'])
  onClick(event: any): void {
    event.stopPropagation();
    const eventTarget = event.target;
    const clickedInside = this.elementRef.nativeElement.contains(eventTarget);

    if (!clickedInside && !this.isOneOf(eventTarget) && !this.isEditHenkiloBtn(eventTarget)) {
      this.clickOutside.emit(null);
    }
  }

  isEditHenkiloBtn(eventTarget: any): boolean {
    if (!eventTarget) {
      return false;
    }
    const elem = eventTarget;
    if (elem.classList.contains('henkilo-list-edit-btn')) {
      return true;
    }
    return false;
  }

  isOneOf(eventTarget: any): boolean {
    if (!eventTarget) {
      return false;
    }
    const id = eventTarget.id;
    if (id === 'henkiloModal') {
      return true;
    }
    return false;
  }
}
