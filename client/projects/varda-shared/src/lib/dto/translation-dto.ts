export interface TranslationDTO {
  accesscount: number;
  id: number;
  category: string;
  key: string;
  accessed: number;
  created: string;
  createdBy: string;
  modified: string;
  modifiedBy: string;
  force: boolean;
  locale: string;
  value: string;
}


export interface AngularTranslateDTO {
  [key: string]: string;
}
