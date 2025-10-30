import { DateTime } from 'luxon';

export interface TransferOutageSearchFilter {
  cursor?: string | null;
  page_size: number;
  timestamp_before?: DateTime;
  timestamp_after?: DateTime;
  vakajarjestaja?: string;
  lahdejarjestelma?: string;
  username?: string;
  ordering?: string;
  group_by: string;
  active_organizations?: boolean;
  company_type?: string;
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
