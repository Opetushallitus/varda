export class VardaPageDto<T> {
  count: number;
  next?: string;
  previous?: string;
  results: Array<T>;
}
