import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
declare var $: any;

@Injectable({
  providedIn: 'root'
})
export class VardaDomService {

  initInstructionsSubject = new Subject<boolean>();

  constructor() { }

  bindTabAndClickEvents(): void {
    $(document).keydown(this.bindTabbing.bind(this));
    $(document).mousedown(this.bindClicking.bind(this));
  }

  bindTabbing(e: any): void {
    if (e.keyCode === 9) {
      document.body.classList.remove('user-is-clicking');
      document.body.classList.add('user-is-tabbing');
    }
  }

  bindClicking(e: any): void {
    document.body.classList.remove('user-is-tabbing');
    document.body.classList.add('user-is-clicking');
  }
}
