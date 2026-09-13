import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api/client";
import type { EditPartyInput, NewPartyInput, Party } from "./api/client";
import { ApiError } from "./api/types";
import { AddPartyForm } from "./components/AddPartyForm";
import { WaitingList } from "./components/WaitingList";
import { RecentlyClosed } from "./components/RecentlyClosed";
import { EditPartyModal } from "./components/EditPartyModal";
import { Toast, type ToastData } from "./components/Toast";

const POLL_INTERVAL_MS = 30_000;
const RECENTLY_CLOSED_LIMIT = 10;

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return fallback;
}

export default function App() {
  const [waiting, setWaiting] = useState<Party[]>([]);
  const [closed, setClosed] = useState<Party[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busyIds, setBusyIds] = useState<Set<string>>(new Set());
  const [editingParty, setEditingParty] = useState<Party | null>(null);
  const [toast, setToast] = useState<ToastData | null>(null);
  const toastIdRef = useRef(0);

  const showToast = useCallback((message: string, actionLabel?: string, onAction?: () => void) => {
    toastIdRef.current += 1;
    setToast({ id: toastIdRef.current, message, actionLabel, onAction });
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [waitingList, seated, noShow, cancelled] = await Promise.all([
        api.listParties("waiting"),
        api.listParties("seated"),
        api.listParties("no_show"),
        api.listParties("cancelled"),
      ]);
      setWaiting(waitingList);
      const recentlyClosed = [...seated, ...noShow, ...cancelled]
        .sort((a, b) => new Date(b.ended_at ?? 0).getTime() - new Date(a.ended_at ?? 0).getTime())
        .slice(0, RECENTLY_CLOSED_LIMIT);
      setClosed(recentlyClosed);
      setLoadError(null);
    } catch (err) {
      setLoadError(errorMessage(err, "Could not load the waitlist."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refresh]);

  function withBusy<T>(id: string, fn: () => Promise<T>): Promise<T> {
    setBusyIds((prev) => new Set(prev).add(id));
    return fn().finally(() => {
      setBusyIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    });
  }

  async function handleAdd(input: NewPartyInput) {
    await api.addParty(input);
    await refresh();
  }

  async function handleSeat(party: Party) {
    try {
      await withBusy(party.id, () => api.seatParty(party.id));
      await refresh();
    } catch (err) {
      showToast(errorMessage(err, `Could not seat ${party.name}.`));
      await refresh();
    }
  }

  async function handleNoShow(party: Party) {
    try {
      await withBusy(party.id, () => api.noShowParty(party.id));
      await refresh();
      showToast(`${party.name} marked no-show.`, "Undo", async () => {
        await api.restoreParty(party.id);
        await refresh();
      });
    } catch (err) {
      showToast(errorMessage(err, `Could not update ${party.name}.`));
      await refresh();
    }
  }

  async function handleCancel(party: Party) {
    try {
      await withBusy(party.id, () => api.cancelParty(party.id));
      await refresh();
      showToast(`${party.name} cancelled.`, "Undo", async () => {
        await api.restoreParty(party.id);
        await refresh();
      });
    } catch (err) {
      showToast(errorMessage(err, `Could not cancel ${party.name}.`));
      await refresh();
    }
  }

  async function handleRestore(party: Party) {
    try {
      await withBusy(party.id, () => api.restoreParty(party.id));
      await refresh();
      showToast(`${party.name} restored to the waitlist.`);
    } catch (err) {
      showToast(errorMessage(err, `Could not restore ${party.name}.`));
      await refresh();
    }
  }

  async function handleEditSave(id: string, input: EditPartyInput) {
    await api.updateParty(id, input);
    await refresh();
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Host Stand</h1>
        {loadError && (
          <p className="banner banner-error" role="alert">
            {loadError}
          </p>
        )}
      </header>

      <AddPartyForm onAdd={handleAdd} />

      <main>
        <section className="waiting-section">
          <h2>
            Waiting {loading ? "" : <span className="count-badge">{waiting.length}</span>}
          </h2>
          {loading ? (
            <p className="loading-state">Loading…</p>
          ) : (
            <WaitingList
              parties={waiting}
              busyIds={busyIds}
              onSeat={handleSeat}
              onNoShow={handleNoShow}
              onCancel={handleCancel}
              onEdit={setEditingParty}
            />
          )}
        </section>

        {!loading && <RecentlyClosed parties={closed} busyIds={busyIds} onRestore={handleRestore} />}
      </main>

      {editingParty && (
        <EditPartyModal party={editingParty} onSave={handleEditSave} onClose={() => setEditingParty(null)} />
      )}

      {toast && <Toast toast={toast} onDismiss={() => setToast(null)} />}
    </div>
  );
}
