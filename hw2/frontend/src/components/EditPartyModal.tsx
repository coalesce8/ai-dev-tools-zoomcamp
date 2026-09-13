import { useState } from "react";
import type { EditPartyInput, Party } from "../api/client";

interface EditPartyModalProps {
  party: Party;
  onSave: (id: string, input: EditPartyInput) => Promise<void>;
  onClose: () => void;
}

export function EditPartyModal({ party, onSave, onClose }: EditPartyModalProps) {
  const [name, setName] = useState(party.name);
  const [partySize, setPartySize] = useState(String(party.party_size));
  const [phone, setPhone] = useState(party.phone ?? "");
  const [quote, setQuote] = useState(party.quoted_minutes != null ? String(party.quoted_minutes) : "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const trimmedName = name.trim();
    const size = Number(partySize);
    if (trimmedName.length === 0) {
      setError("Name is required.");
      return;
    }
    if (!Number.isInteger(size) || size < 1) {
      setError("Party size must be at least 1.");
      return;
    }

    setSaving(true);
    try {
      await onSave(party.id, {
        name: trimmedName,
        party_size: size,
        phone: phone.trim() || null,
        quoted_minutes: quote.trim() === "" ? null : Number(quote),
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save changes.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <h2>Edit party</h2>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="edit-name">Name</label>
            <input
              id="edit-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={80}
              autoFocus
              required
            />
          </div>
          <div className="field">
            <label htmlFor="edit-size">Size</label>
            <input
              id="edit-size"
              type="number"
              inputMode="numeric"
              min={1}
              value={partySize}
              onChange={(e) => setPartySize(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="edit-phone">Phone</label>
            <input
              id="edit-phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              maxLength={32}
            />
          </div>
          <div className="field">
            <label htmlFor="edit-quote">Quote, minutes</label>
            <input
              id="edit-quote"
              type="number"
              inputMode="numeric"
              min={0}
              value={quote}
              onChange={(e) => setQuote(e.target.value)}
            />
          </div>
          {error && (
            <p className="field-error" role="alert">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
