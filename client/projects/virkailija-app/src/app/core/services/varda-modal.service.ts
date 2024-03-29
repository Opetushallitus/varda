import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';

@Injectable()
export class VardaModalService {
  private formValuesChanged$ = new Subject<boolean>();
  private modalOpen$ = new Subject<boolean>();
  private modalCloseWithoutConfirmation$ = new Subject<boolean>();

  private henkiloFormSubject = new Subject<any>();
  private fileUploadFormSubject = new Subject<any>();
  private toimipaikkaSuccessModalSubject = new Subject<any>();
  private toimipaikkaDeleteSuccessModalSubject = new Subject<any>();
  private lapsiSuccessModalSubject = new Subject<any>();

  constructor() { }

  openModal(modalName: string, isOpen: boolean, data?: any): void {
    let subject;
    if (modalName === 'toimipaikkaSuccessModal') {
      subject = this.toimipaikkaSuccessModalSubject;
    } else if (modalName === 'toimipaikkaDeleteSuccessModal') {
      subject = this.toimipaikkaDeleteSuccessModalSubject;
    } else if (modalName === 'fileUploadForm') {
      subject = this.fileUploadFormSubject;
    } else if (modalName === 'henkiloForm') {
      subject = this.henkiloFormSubject;
    } else if (modalName === 'lapsiSuccessModal') {
      subject = this.lapsiSuccessModalSubject;
    }
    subject.next({ isOpen, data });
  }

  modalOpenObs(modalName: string): Observable<any> {
    let obs;
    if (modalName === 'toimipaikkaSuccessModal') {
      obs = this.toimipaikkaSuccessModalSubject.asObservable();
    } else if (modalName === 'toimipaikkaDeleteSuccessModal') {
      obs = this.toimipaikkaDeleteSuccessModalSubject.asObservable();
    } else if (modalName === 'fileUploadForm') {
      obs = this.fileUploadFormSubject.asObservable();
    } else if (modalName === 'henkiloForm') {
      obs = this.henkiloFormSubject.asObservable();
    } else if (modalName === 'lapsiSuccessModal') {
      obs = this.lapsiSuccessModalSubject.asObservable();
    }
    return obs;
  }

  setFormValuesChanged(value: boolean) {
    this.formValuesChanged$.next(value);
  }

  getFormValuesChanged(): Observable<boolean> {
    return this.formValuesChanged$.asObservable();
  }

  setModalOpen(isOpen: boolean) {
    this.modalOpen$.next(isOpen);
  }

  getModalOpen(): Observable<boolean> {
    return this.modalOpen$.asObservable();
  }

  getModalCloseWithoutConfirmation(): Observable<boolean> {
    return this.modalCloseWithoutConfirmation$;
  }

  setModalCloseWithoutConfirmation(isCloseWithoutConfirmation: boolean) {
    this.modalCloseWithoutConfirmation$.next(isCloseWithoutConfirmation);
  }
}
