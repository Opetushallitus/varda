import { Moment } from 'moment';

export interface RequestSummarySearchFilter {
  page: number;
  count: number;
  page_size: number;
  categories?: { [key: string]: boolean };
  summary_date_before?: Moment;
  summary_date_after?: Moment;
  vakajarjestaja?: string;
  lahdejarjestelma?: string;
  username?: string;
  request_url_simple?: string;
  search?: string;
  group?: string;
}

export interface RequestCount {
  request_url_simple: string;
  request_method: string;
  response_code: string;
  count: number;
  successful: boolean;
}

export interface RequestSummary {
  user_id?: number;
  username?: string;
  vakajarjestaja_id?: number;
  vakajarjestaja_nimi?: string;
  vakajarjestaja_oid?: string;
  lahdejarjestelma?: string;
  request_url_simple?: string;
  successful_count: string;
  unsuccessful_count: string;
  ratio: number;
  summary_date: string;
  request_counts: Array<RequestCount>;
}
