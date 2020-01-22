import { VardaField } from './varda-field.model';
export class VardaFieldSet {
    id?: string;
    title?: string;
    fields?: Array<VardaField>;
}

export class VardaFieldsetArrayContainer {
  fieldsets: Array<VardaFieldSet>;
}
