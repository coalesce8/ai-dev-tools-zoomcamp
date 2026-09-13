export type PartyStatus = "waiting" | "seated" | "no_show" | "cancelled";

/** Matches the server response shape from spec.md §3 — already enriched, no client-side date math. */
export interface Party {
  id: string;
  name: string;
  party_size: number;
  phone: string | null;
  quoted_minutes: number | null;
  status: PartyStatus;
  created_at: string;
  ended_at: string | null;
  position: number | null;
  waiting_minutes: number;
  is_overdue: boolean;
}

export interface NewPartyInput {
  name: string;
  party_size: number;
  phone?: string | null;
  quoted_minutes?: number | null;
}

export interface EditPartyInput {
  name?: string;
  party_size?: number;
  phone?: string | null;
  quoted_minutes?: number | null;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}
