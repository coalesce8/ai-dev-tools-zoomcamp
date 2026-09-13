import { useState } from "react";
import type { Party, PartyStatus } from "../api/client";

interface RecentlyClosedProps {
  parties: Party[];
  busyIds: Set<string>;
  onRestore: (party: Party) => void;
}

const STATUS_LABEL: Record<PartyStatus, string> = {
  waiting: "Waiting",
  seated: "Seated",
  no_show: "No-show",
  cancelled: "Cancelled",
};

export function RecentlyClosed({ parties, busyIds, onRestore }: RecentlyClosedProps) {
  const [open, setOpen] = useState(false);

  return (
    <section className="recently-closed">
      <button
        type="button"
        className="recently-closed-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>Recently closed ({parties.length})</span>
        <span className={`chevron${open ? " chevron-open" : ""}`} aria-hidden="true">
          ▸
        </span>
      </button>
      {open && (
        <ul className="party-list party-list-closed">
          {parties.length === 0 && <li className="empty-state-inline">Nothing closed yet.</li>}
          {parties.map((party) => (
            <li key={party.id} className="party-row party-row-closed">
              <div className="party-row-main">
                <span className={`badge badge-status badge-${party.status}`}>{STATUS_LABEL[party.status]}</span>
                <div className="party-info">
                  <div className="party-name-line">
                    <span className="party-name">{party.name}</span>
                    <span className="party-size">party of {party.party_size}</span>
                  </div>
                  <div className="party-meta">
                    <span>waited {party.waiting_minutes} min</span>
                    {party.phone && <span className="party-phone">{party.phone}</span>}
                  </div>
                </div>
              </div>
              <div className="party-actions">
                <button
                  type="button"
                  className="btn btn-restore"
                  disabled={busyIds.has(party.id)}
                  onClick={() => onRestore(party)}
                >
                  Restore
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
