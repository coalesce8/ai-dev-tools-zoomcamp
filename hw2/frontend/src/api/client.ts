import { ApiError, type EditPartyInput, type NewPartyInput, type Party, type PartyStatus } from "./types";

export type { ApiError } from "./types";
export type { EditPartyInput, NewPartyInput, Party, PartyStatus } from "./types";

/**
 * Single entry point for every backend call the app makes. Talks to the real FastAPI
 * service (see hw2/backend) over HTTP.
 */
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(0, "Unable to reach the server.");
  }

  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      if (body?.detail) message = body.detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  listParties(status: PartyStatus = "waiting"): Promise<Party[]> {
    return request(`/api/parties?status=${encodeURIComponent(status)}`);
  },

  addParty(input: NewPartyInput): Promise<Party> {
    return request("/api/parties", { method: "POST", body: JSON.stringify(input) });
  },

  updateParty(id: string, input: EditPartyInput): Promise<Party> {
    return request(`/api/parties/${id}`, { method: "PATCH", body: JSON.stringify(input) });
  },

  seatParty(id: string): Promise<Party> {
    return request(`/api/parties/${id}/seat`, { method: "POST" });
  },

  noShowParty(id: string): Promise<Party> {
    return request(`/api/parties/${id}/no-show`, { method: "POST" });
  },

  cancelParty(id: string): Promise<Party> {
    return request(`/api/parties/${id}/cancel`, { method: "POST" });
  },

  restoreParty(id: string): Promise<Party> {
    return request(`/api/parties/${id}/restore`, { method: "POST" });
  },

  health(): Promise<{ status: string }> {
    return request("/api/health");
  },
};
