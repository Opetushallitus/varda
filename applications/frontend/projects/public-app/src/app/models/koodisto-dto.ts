import { CodeDto } from './code-dto';

export interface KoodistoDto {
  name: string;
  version: number;
  update_datetime: string;
  codes: Array<CodeDto>;
}
