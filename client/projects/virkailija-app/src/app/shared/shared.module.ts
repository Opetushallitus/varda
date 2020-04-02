import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { NgcCookieConsentModule, NgcCookieConsentConfig } from 'ngx-cookieconsent';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatRadioModule } from '@angular/material/radio';
import { MatStepperModule } from '@angular/material/stepper';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatMomentDateModule, MAT_MOMENT_DATE_ADAPTER_OPTIONS } from '@angular/material-moment-adapter';
import { MAT_DATE_FORMATS, MAT_DATE_LOCALE } from '@angular/material/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import {
  PageNotFoundComponent,
  VardaIconComponent,
  VardaAccessibilitySettingsComponent,
  VardaInfoModalComponent,
  VardaModalFormComponent,
  VardaFormQuestionComponent,
  VardaSuccessModalComponent
} from '../utilities/components';
import { HighlightElementDirective } from './directives/highlight-element.directive';
import { HighContrastDirective } from './directives/high-contrast.directive';
import { ClickOutsideDirective } from './directives/click-outside.directive';
import { KoodistoDisplayvalueDirective } from './directives/koodisto-displayvalue.directive';
import { VardaDatePipe } from './pipes/varda-date.pipe';
import { KeysPipe } from './pipes/keys.pipe';
import { VardaDeleteButtonComponent } from './components/varda-delete-button/varda-delete-button.component';
import { VardaToggleButtonComponent } from './components/varda-toggle-button/varda-toggle-button.component';
import { VardaErrorAlertComponent } from './components/varda-error-alert/varda-error-alert.component';
import { VardaPromptModalComponent } from './components/varda-prompt-modal/varda-prompt-modal.component';
import { VardaDropdownFilterComponent } from './components/varda-dropdown-filter/varda-dropdown-filter.component';
import { VardaListPaginationComponent } from './components/varda-list-pagination/varda-list-pagination.component';
import { VardaRadioButtonGroupComponent } from './components/varda-radio-button-group/varda-radio-button-group.component';
import { VardaRadioButtonComponent } from './components/varda-radio-button-group/varda-radio-button/varda-radio-button.component';
import { BrowserNotSupportedComponent } from './components/browser-not-supported/browser-not-supported.component';
import { BrowserNotSupportedGuard } from './components/browser-not-supported/browser-not-supported.guard';
import { SlideHideDirective } from './directives/slide-hide.directive';
import { VardaDatepickerComponent } from './components/varda-datepicker/varda-datepicker.component';
import { VardaDateService } from '../varda-main/services/varda-date.service';
import { VardaDatepickerHeaderComponent } from './components/varda-datepicker/varda-datepicker-header/varda-datepicker-header.component';


const cookieConfig: NgcCookieConsentConfig = {
  cookie: {
    domain: ''
  },
  position: 'bottom',
  theme: 'classic',
  palette: {
    popup: {
      background: '#000',
      text: '#fff',
      link: '#fff'
    },
    button: {
      background: '#f1d600',
      text: '#000',
      border: 'transparent'
    }
  },
  type: 'info',
  content: {
    message: 'This uses cookies to ensure you get the best experience on our website.',
    dismiss: 'OK',
    link: ''
  }
};

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCheckboxModule,
    BrowserAnimationsModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatExpansionModule,
    MatRadioModule,
    MatAutocompleteModule,
    MatListModule,
    MatCardModule,
    MatMenuModule,
    MatDatepickerModule,
    MatMomentDateModule,
    TranslateModule,
    NgcCookieConsentModule.forRoot(cookieConfig)
  ],
  declarations: [
    PageNotFoundComponent,
    HighlightElementDirective,
    HighContrastDirective,
    VardaIconComponent,
    VardaAccessibilitySettingsComponent,
    VardaInfoModalComponent,
    ClickOutsideDirective,
    KoodistoDisplayvalueDirective,
    VardaDatePipe,
    KeysPipe,
    VardaInfoModalComponent,
    VardaModalFormComponent,
    VardaFormQuestionComponent,
    VardaSuccessModalComponent,
    VardaDeleteButtonComponent,
    VardaToggleButtonComponent,
    VardaErrorAlertComponent,
    VardaPromptModalComponent,
    VardaDropdownFilterComponent,
    VardaListPaginationComponent,
    VardaRadioButtonGroupComponent,
    VardaRadioButtonComponent,
    BrowserNotSupportedComponent,
    SlideHideDirective,
    VardaDatepickerComponent,
    VardaDatepickerHeaderComponent],
  providers: [
    BrowserNotSupportedGuard,
    {
      provide: MAT_DATE_LOCALE, useValue: 'fi-FI'
    },
    {
      provide: MAT_DATE_FORMATS,
      useValue: {
        parse: {
          dateInput: VardaDateService.vardaDefaultDateFormat,
        },
        display: {
          dateInput: 'DD.MM.YYYY',
          monthYearLabel: 'MMMM YYYY',
          dateA11yLabel: 'LL',
          monthYearA11yLabel: 'MMMM YYYY',
        },
      }
    },
    {
      provide: MAT_MOMENT_DATE_ADAPTER_OPTIONS, useValue: { strict: true }
    }
  ],
  exports: [
    HighlightElementDirective,
    HighContrastDirective,
    ClickOutsideDirective,
    KoodistoDisplayvalueDirective,
    VardaIconComponent,
    VardaAccessibilitySettingsComponent,
    VardaInfoModalComponent,
    VardaModalFormComponent,
    VardaFormQuestionComponent,
    VardaSuccessModalComponent,
    VardaDatePipe,
    KeysPipe,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatExpansionModule,
    MatRadioModule,
    MatAutocompleteModule,
    MatListModule,
    MatCardModule,
    BrowserAnimationsModule,
    NgcCookieConsentModule,
    VardaDeleteButtonComponent,
    VardaToggleButtonComponent,
    VardaErrorAlertComponent,
    VardaPromptModalComponent,
    VardaDropdownFilterComponent,
    VardaListPaginationComponent,
    VardaRadioButtonGroupComponent,
    VardaRadioButtonComponent,
    BrowserNotSupportedComponent,
    SlideHideDirective,
    VardaDatepickerComponent
  ],
  entryComponents: [ VardaDatepickerHeaderComponent ]
})
export class SharedModule { }
