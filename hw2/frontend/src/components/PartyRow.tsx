import type { Party } from "../api/client";

interface PartyRowProps {
  party: Party;
  busy: boolean;
  onSeat: (party: Party) => void;
  onNoShow: (party: Party) => void;
  onCancel: (party: Party) => void;
  onEdit: (party: Party) => void;
}

export function PartyRow({ party, busy, onSeat, onNoShow, onCancel, onEdit }: PartyRowProps) {
  return (
    <li className={`party-row${party.is_overdue ? " party-row-overdue" : ""}`}>
      <div className="party-row-main">
        <div className="party-position" aria-hidden="true">
          {party.position ?? "–"}
        </div>
        <div className="party-info">
          <div className="party-name-line">
            <span className="party-name">{party.name}</span>
            <span className="party-size">party of {party.party_size}</span>
            {party.is_overdue && (
              <span className="badge badge-overdue" title="Past the quoted wait">
                ⚠ overdue
              </span>
            )}
          </div>
          <div className="party-meta">
            <span>
              waiting <strong>{party.waiting_minutes}</strong> min
            </span>
            {party.quoted_minutes != null && <span>quoted {party.quoted_minutes} min</span>}
            {party.phone && <span className="party-phone">{party.phone}</span>}
          </div>
        </div>
      </div>
      <div className="party-actions">
        <button type="button" className="btn btn-seat" disabled={busy} onClick={() => onSeat(party)}>
          Seat
        </button>
        <button type="button" className="btn btn-noshow" disabled={busy} onClick={() => onNoShow(party)}>
          No-show
        </button>
        <button type="button" className="btn btn-cancel" disabled={busy} onClick={() => onCancel(party)}>
          Cancel
        </button>
        <button type="button" className="btn btn-edit" disabled={busy} onClick={() => onEdit(party)}>
          Edit
        </button>
      </div>
    </li>
  );
}
