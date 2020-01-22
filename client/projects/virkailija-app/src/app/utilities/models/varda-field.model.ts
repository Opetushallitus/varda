import { VardaFieldDisplayName } from './varda-field-display-name.model';
import { VardaFieldPlaceholderText } from './varda-field-placeholder-text.model';
import { VardaFieldInstructionText } from './varda-field-instruction-text.model';
import { VardaFieldStyles } from './varda-field-styles.model';
import { VardaFieldRules } from './varda-field-rules.model';

export class VardaField {
    key?: string;
    displayName?: VardaFieldDisplayName;
    widget?: string;
    instructionText?: VardaFieldInstructionText;
    placeholder?: VardaFieldPlaceholderText;
    rules?: VardaFieldRules;
    isReadonly?: boolean;
    styles?: VardaFieldStyles;
    hidden?: boolean;
    options?: Array<any>;
    koodisto?: string;
    value?: string;
}
