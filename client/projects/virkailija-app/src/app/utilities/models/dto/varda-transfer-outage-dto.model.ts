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
}

export interface TransferOutageUser {
  user_id: number;
  username: string;
  vakajarjestaja_id: number;
  vakajarjestaja_nimi: string;
  vakajarjestaja_oid: string;
  last_successful: string;
  last_unsuccessful: string;
}

export interface TransferOutageLahdejarjestelma {
  lahdejarjestelma: string;
  last_successful: string;
  last_unsuccessful: string;
}
