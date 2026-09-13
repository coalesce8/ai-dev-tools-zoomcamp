import type { Party } from "../api/client";
import { PartyRow } from "./PartyRow";

interface WaitingListProps {
  parties: Party[];
  busyIds: Set<string>;
  onSeat: (party: Party) => void;
  onNoShow: (party: Party) => void;
  onCancel: (party: Party) => void;
  onEdit: (party: Party) => void;
}

export function WaitingList({ parties, busyIds, onSeat, onNoShow, onCancel, onEdit }: WaitingListProps) {
  if (parties.length === 0) {
    return (
      <div className="empty-state">
        <p>No one waiting. Add a walk-in above.</p>
      </div>
    );
  }

  return (
    <ul className="party-list">
      {parties.map((party) => (
        <PartyRow
          key={party.id}
          party={party}
          busy={busyIds.has(party.id)}
          onSeat={onSeat}
          onNoShow={onNoShow}
          onCancel={onCancel}
          onEdit={onEdit}
        />
      ))}
    </ul>
  );
}
