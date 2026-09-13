import { useRef, useState } from "react";
import type { NewPartyInput } from "../api/client";

interface AddPartyFormProps {
  onAdd: (input: NewPartyInput) => Promise<void>;
}

export function AddPartyForm({ onAdd }: AddPartyFormProps) {
  const [name, setName] = useState("");
  const [partySize, setPartySize] = useState("1");
  const [phone, setPhone] = useState("");
  const [quote, setQuote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const nameRef = useRef<HTMLInputElement>(null);

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

    const input: NewPartyInput = {
      name: trimmedName,
      party_size: size,
      phone: phone.trim() || undefined,
      quoted_minutes: quote.trim() === "" ? undefined : Number(quote),
    };

    setSubmitting(true);
    try {
      await onAdd(input);
      setName("");
      setPartySize("1");
      setPhone("");
      setQuote("");
      nameRef.current?.focus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add party.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="add-form" onSubmit={handleSubmit}>
      <div className="add-form-fields">
        <div className="field field-name">
          <label htmlFor="party-name">Name</label>
          <input
            id="party-name"
            ref={nameRef}
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Guest name"
            maxLength={80}
            autoFocus
            required
          />
        </div>
        <div className="field field-size">
          <label htmlFor="party-size">Size</label>
          <input
            id="party-size"
            type="number"
            inputMode="numeric"
            min={1}
            value={partySize}
            onChange={(e) => setPartySize(e.target.value)}
            required
          />
        </div>
        <div className="field field-phone">
          <label htmlFor="party-phone">Phone (optional)</label>
          <input
            id="party-phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="555-0100"
            maxLength={32}
          />
        </div>
        <div className="field field-quote">
          <label htmlFor="party-quote">Quote, min (optional)</label>
          <input
            id="party-quote"
            type="number"
            inputMode="numeric"
            min={0}
            value={quote}
            onChange={(e) => setQuote(e.target.value)}
            placeholder="20"
          />
        </div>
        <button type="submit" className="btn btn-primary btn-add" disabled={submitting}>
          {submitting ? "Adding…" : "Add to waitlist"}
        </button>
      </div>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
