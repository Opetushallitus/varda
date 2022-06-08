import { Moment } from 'moment';

export interface TransferOutageSearchFilter {
  page: number;
  count: number;
  page_size: number;
  timestamp_before?: Moment;
  timestamp_after?: Moment;
  vakajarjestaja?: string;
  lahdejarjestelma?: string;
  username?: string;
  ordering?: string;
  group_by: string;
}

export interface TransferOutage {
  user_id?: number;
  username?: string;
  vakajarjestaja_id?: number;
  vakajarjestaja_nimi?: string;
  vakajarjestaja_oid?: string;
  lahdejarjestelma?: string;
  last_successful_max?: string;
  last_unsuccessful_max?: string;
}
