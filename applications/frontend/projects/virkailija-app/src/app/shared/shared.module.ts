import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
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
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBarModule, MAT_SNACK_BAR_DEFAULT_OPTIONS } from '@angular/material/snack-bar';
import { MatLuxonDateModule, MAT_LUXON_DATE_ADAPTER_OPTIONS } from '@angular/material-luxon-adapter';
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
import { MatPaginatorIntl, MatPaginatorModule, MAT_PAGINATOR_DEFAULT_OPTIONS } from '@angular/material/paginator';
import { VardaMatPaginator } from './components/varda-paginator/varda-paginator.class';
import { ToimipaikkaNimiDirective } from './directives/toimipaikka-nimi.directive';
import { MatSortModule } from '@angular/material/sort';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { VardaAutocompleteSelectorComponent } from './components/varda-autocomplete-selector/varda-autocomplete-selector.component';
import { SnackbarTimers } from '../core/services/varda-snackbar.service';
import { BrowserNotSupportedGuard } from '../varda-main/components/public-components/public-components';
import { RoboIdComponent } from './components/robo-id/robo-id.component';
import { VardaInputComponent } from './components/varda-input/varda-input.component';
import { VardaShowMoreLessComponent } from './components/varda-show-more-less/varda-show-more-less.component';
import { ScrollingModule } from '@angular/cdk/scrolling';
import { VardaSelectComponent } from './varda-select/varda-select.component';
import {TruncateWordsPipe} from "./pipes/truncate-words.pipe";

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
    MatLuxonDateModule,
    MatPaginatorModule,
    MatSortModule,
    MatTabsModule,
    MatChipsModule,
    MatButtonToggleModule,
    ScrollingModule,
    TranslateModule
  ],
  declarations: [
    HighlightElementDirective,
    HighContrastDirective,
    VardaAccessibilitySettingsComponent,
    ClickOutsideDirective,
    KeysPipe,
    TruncateWordsPipe,
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
    VardaSelectComponent,
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
          dateInput: 'dd.MM.yyyy',
          monthYearLabel: 'LLLL yyyy',
          dateA11yLabel: 'DDDD',
          monthYearA11yLabel: 'LLLL yyyy',
        },
      }
    },
    {
      provide: MAT_SNACK_BAR_DEFAULT_OPTIONS, useValue: { duration: SnackbarTimers.normal }
    },
    {
      provide: MAT_LUXON_DATE_ADAPTER_OPTIONS, useValue: { useUtc: true }
    },
    {
      provide: MAT_PAGINATOR_DEFAULT_OPTIONS, useValue: {
        pageSizeOptions: [10, 20, 50, 100],
        pageSize: 20,
        showFirstLastButtons: false
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
    TruncateWordsPipe,
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
})
export class SharedModule { }
