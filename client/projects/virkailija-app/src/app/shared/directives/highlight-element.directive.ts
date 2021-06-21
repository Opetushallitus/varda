import { Directive, ElementRef, HostListener } from '@angular/core';

@Directive({
  selector: '[appHighlightElement]'
})
export class HighlightElementDirective {
  private elem: HTMLElement;
  private highlightContainerSelector = 'varda-highlight-container';
  private highlightLabelSelector = 'varda-highlight-label';
  private fieldSetSelector = 'varda-fieldset';
  private fieldLabelSelector = 'varda-field-label';

  constructor(el: ElementRef) {
    this.elem = el.nativeElement;
  }

  @HostListener('focus') onFocus() {
    const fieldsetNodes = this.getFieldSets();
    const fieldLabels = this.getFieldLabels();
    this.removeHighlight(Array.from(fieldsetNodes), this.highlightContainerSelector);
    this.removeHighlight(Array.from(fieldLabels), this.highlightLabelSelector);
    this.addHighlightToContainer();
    this.addHighlightToLabel();
  }

  removeHighlight(elements: Array<Element>, cssClass: string): void {
    elements.forEach((el: HTMLElement) => el.classList.remove(cssClass));
  }

  addHighlightToContainer(): void {
    const parentContainerElemSelector = this.elem.dataset.parentContainer;
    if (parentContainerElemSelector) {
      const parent = document.getElementById(`${parentContainerElemSelector}`);
      parent.classList.add(this.highlightContainerSelector);
    }
  }

  addHighlightToLabel(): void {
    const label = this.elem.previousElementSibling;
    if (label) {
      label.classList.add(this.highlightLabelSelector);
    }
  }

  getFieldSets(): NodeListOf<Element> {
    return document.querySelectorAll(`.${this.fieldSetSelector}`);
  }

  getFieldLabels(): NodeListOf<Element> {
    return document.querySelectorAll(`.${this.fieldLabelSelector}`);
  }
}
