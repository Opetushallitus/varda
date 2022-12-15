import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { NgcCookieConsentModule, NgcCookieConsentConfig } from 'ngx-cookieconsent';
import { MatLegacyAutocompleteModule as MatAutocompleteModule } from '@angular/material/legacy-autocomplete';
import { MatLegacyButtonModule as MatButtonModule } from '@angular/material/legacy-button';
import { MatLegacyCardModule as MatCardModule } from '@angular/material/legacy-card';
import { MatLegacyCheckboxModule as MatCheckboxModule } from '@angular/material/legacy-checkbox';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatLegacyFormFieldModule as MatFormFieldModule } from '@angular/material/legacy-form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatLegacyInputModule as MatInputModule } from '@angular/material/legacy-input';
import { MatLegacyListModule as MatListModule } from '@angular/material/legacy-list';
import { MatLegacyMenuModule as MatMenuModule } from '@angular/material/legacy-menu';
import { MatLegacyRadioModule as MatRadioModule } from '@angular/material/legacy-radio';
import { MatStepperModule } from '@angular/material/stepper';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatLegacySelectModule as MatSelectModule } from '@angular/material/legacy-select';
import { MatLegacySnackBarModule as MatSnackBarModule, MAT_LEGACY_SNACK_BAR_DEFAULT_OPTIONS as MAT_SNACK_BAR_DEFAULT_OPTIONS } from '@angular/material/legacy-snack-bar';
import { MatMomentDateModule, MAT_MOMENT_DATE_ADAPTER_OPTIONS } from '@angular/material-moment-adapter';
import { MAT_DATE_FORMATS, MAT_DATE_LOCALE } from '@angular/material/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import {
  VardaAccessibilitySettingsComponent,
  VardaModalFormComponent,
  VardaSuccessModalComponent,
  VardaFormFieldComponent
} from '../utilities/components';
import { HighlightElementDirective } from './directives/highlight-element.directive';
import { HighContrastDirective } from './directives/high-contrast.directive';
import { ClickOutsideDirective } from './directives/click-outside.directive';
import { KeysPipe } from './pipes/keys.pipe';
import { VardaDeleteButtonComponent } from './components/varda-delete-button/varda-delete-button.component';
import { VardaToggleButtonComponent } from './components/varda-toggle-button/varda-toggle-button.component';
import { VardaErrorAlertComponent } from './components/varda-error-alert/varda-error-alert.component';
import { VardaPromptModalComponent } from './components/varda-prompt-modal/varda-prompt-modal.component';
import { VardaDropdownFilterComponent } from './components/varda-dropdown-filter/varda-dropdown-filter.component';
import { VardaRadioButtonGroupComponent } from './components/varda-radio-button-group/varda-radio-button-group.component';
import { VardaRadioButtonComponent } from './components/varda-radio-button-group/varda-radio-button/varda-radio-button.component';
import { SlideHideDirective } from './directives/slide-hide.directive';
import { VardaDatepickerComponent } from './components/varda-datepicker/varda-datepicker.component';
import { VardaDateService } from 'varda-shared';
import { VardaDatepickerHeaderComponent } from './components/varda-datepicker/varda-datepicker-header/varda-datepicker-header.component';
import { MatLegacyPaginatorIntl as MatPaginatorIntl, MatLegacyPaginatorModule as MatPaginatorModule, MAT_LEGACY_PAGINATOR_DEFAULT_OPTIONS as MAT_PAGINATOR_DEFAULT_OPTIONS } from '@angular/material/legacy-paginator';
import { VardaMatPaginator } from './components/varda-paginator/varda-paginator.class';
import { ToimipaikkaNimiDirective } from './directives/toimipaikka-nimi.directive';
import { MatSortModule } from '@angular/material/sort';
import { MatLegacyTabsModule as MatTabsModule } from '@angular/material/legacy-tabs';
import { MatLegacyChipsModule as MatChipsModule } from '@angular/material/legacy-chips';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { VardaAutocompleteSelectorComponent } from './components/varda-autocomplete-selector/varda-autocomplete-selector.component';
import { SnackbarTimers } from '../core/services/varda-snackbar.service';
import { BrowserNotSupportedGuard } from '../varda-main/components/public-components/public-components';
import { RoboIdComponent } from './components/robo-id/robo-id.component';
import { VardaInputComponent } from './components/varda-input/varda-input.component';
import { VardaShowMoreLessComponent } from './components/varda-show-more-less/varda-show-more-less.component';
import { ScrollingModule } from '@angular/cdk/scrolling';
import { VardaSelectComponent } from './varda-select/varda-select.component';

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
    MatSelectModule,
    MatSnackBarModule,
    MatDatepickerModule,
    MatMomentDateModule,
    MatPaginatorModule,
    MatSortModule,
    MatTabsModule,
    MatChipsModule,
    MatButtonToggleModule,
    ScrollingModule,
    TranslateModule,
    NgcCookieConsentModule.forRoot(cookieConfig)
  ],
  declarations: [
    HighlightElementDirective,
    HighContrastDirective,
    VardaAccessibilitySettingsComponent,
    ClickOutsideDirective,
    KeysPipe,
    VardaModalFormComponent,
    VardaFormFieldComponent,
    VardaSuccessModalComponent,
    VardaDeleteButtonComponent,
    VardaToggleButtonComponent,
    VardaErrorAlertComponent,
    VardaPromptModalComponent,
    VardaDropdownFilterComponent,
    VardaRadioButtonGroupComponent,
    VardaRadioButtonComponent,
    SlideHideDirective,
    ToimipaikkaNimiDirective,
    VardaDatepickerComponent,
    VardaDatepickerHeaderComponent,
    VardaAutocompleteSelectorComponent,
    RoboIdComponent,
    VardaInputComponent,
    VardaShowMoreLessComponent,
    VardaSelectComponent
  ],
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
      provide: MAT_SNACK_BAR_DEFAULT_OPTIONS, useValue: { duration: SnackbarTimers.normal }
    },
    {
      provide: MAT_MOMENT_DATE_ADAPTER_OPTIONS, useValue: { strict: true }
    },
    {
      provide: MAT_PAGINATOR_DEFAULT_OPTIONS, useValue: {
        pageSizeOptions: [10, 20, 50, 100],
        pageSize: 20,
        showFirstLastButtons: true
      }
    },
    { provide: MatPaginatorIntl, useClass: VardaMatPaginator },
    MatSortModule
  ],
  exports: [
    HighlightElementDirective,
    HighContrastDirective,
    ClickOutsideDirective,
    VardaAccessibilitySettingsComponent,
    VardaModalFormComponent,
    VardaFormFieldComponent,
    VardaSuccessModalComponent,
    KeysPipe,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatSelectModule,
    MatSnackBarModule,
    MatExpansionModule,
    MatRadioModule,
    MatAutocompleteModule,
    MatListModule,
    MatCardModule,
    MatPaginatorModule,
    MatSortModule,
    MatTabsModule,
    MatChipsModule,
    MatButtonToggleModule,
    BrowserAnimationsModule,
    NgcCookieConsentModule,
    VardaDeleteButtonComponent,
    VardaToggleButtonComponent,
    VardaErrorAlertComponent,
    VardaPromptModalComponent,
    VardaDropdownFilterComponent,
    VardaRadioButtonGroupComponent,
    VardaRadioButtonComponent,
    SlideHideDirective,
    ToimipaikkaNimiDirective,
    VardaDatepickerComponent,
    VardaAutocompleteSelectorComponent,
    RoboIdComponent,
    VardaInputComponent,
    VardaShowMoreLessComponent,
    VardaSelectComponent,
  ],
  entryComponents: [VardaDatepickerHeaderComponent]
})
export class SharedModule { }
