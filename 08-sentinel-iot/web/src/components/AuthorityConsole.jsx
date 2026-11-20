import { useEffect, useState } from 'react';
import {
  CheckCheck,
  Megaphone,
  Radio,
  ShieldAlert,
  Siren,
  TriangleAlert,
  Undo2,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { api } from '../lib/api.js';
import { startSiren, stopSiren, isSirenPlaying } from '../lib/siren.js';
import { formatRelative, riskLabel } from '../lib/format.js';
import { Modal } from './Modal.jsx';
import { RiskBadge } from './RiskBadge.jsx';
import { RiskGauge } from './RiskGauge.jsx';

export function AuthorityConsole({ nodes = [], system, summary, operator, onToast }) {
  const [modal, setModal] = useState(null);
  const [busy, setBusy] = useState(false);
  const [audioActive, setAudioActive] = useState(isSirenPlaying());
  const [evacTarget, setEvacTarget] = useState('all');
  const [evacReason, setEvacReason] = useState(
    'Severe flood risk has exceeded the evacuation trigger at Godavari Ghat.',
  );
  const [sosNode, setSosNode] = useState(nodes[0]?.id ?? '');
  const [override, setOverride] = useState({
    nodeId: nodes[0]?.id ?? '',
    level: 'high',
    note: '',
    durationMinutes: 60,
  });

  const evacuation = system?.evacuation;
  const siren = system?.siren;
  const overrides = nodes.filter((node) => node.override);
  const activeOverridesCount = overrides.length;
  const peakNode = nodes.find((node) => node.id === summary?.peakNode?.id) ?? nodes[0];

  useEffect(() => {
    if (!siren?.enabled && isSirenPlaying()) {
      stopSiren();
      setAudioActive(false);
    }
  }, [siren?.enabled]);

  useEffect(() => {
    if (!override.nodeId && nodes[0]) {
      setOverride((current) => ({ ...current, nodeId: nodes[0].id }));
    }
    if (!sosNode && nodes[0]) setSosNode(nodes[0].id);
  }, [nodes, override.nodeId, sosNode]);

  const run = async (action, successMessage, { closeModal = true, stopAudioOnError = false } = {}) => {
    setBusy(true);
    try {
      const result = await action();
      if (successMessage) onToast?.(successMessage, 'success');
      if (closeModal) setModal(null);
      return result;
    } catch (error) {
      if (stopAudioOnError) {
        stopSiren();
        setAudioActive(false);
      }
      onToast?.(error.message, 'error');
      return null;
    } finally {
      setBusy(false);
    }
  };

  const triggerEvacuation = () => {
    const audioStarted = startSiren();
    if (audioStarted) setAudioActive(true);
    run(
      () =>
        api.issueEvacuation(
          {
            nodeId: evacTarget === 'all' ? null : evacTarget,
            reason: evacReason,
          },
          operator,
        ),
      'Evacuation order broadcast',
      { stopAudioOnError: true },
    );
  };

  const handleAllClear = () => {
    run(() => api.allClear(operator), 'All-clear issued — monitoring resumed').then((result) => {
      if (result) {
        stopSiren();
        setAudioActive(false);
      }
    });
  };

  const handleSirenToggle = async () => {
    const nextEnabled = !siren?.enabled;
    if (nextEnabled) {
      const started = startSiren();
      setAudioActive(started);
    } else {
      stopSiren();
      setAudioActive(false);
    }
    await run(
      () => api.setSiren(nextEnabled, operator),
      nextEnabled ? 'Siren channel activated' : 'Siren channel silenced',
      { closeModal: false },
    );
  };

  const handleLocalAudio = () => {
    if (audioActive) {
      stopSiren();
      setAudioActive(false);
      onToast?.('Console audio silenced', 'neutral');
      return;
    }
    const started = startSiren();
    setAudioActive(started);
    onToast?.(
      started ? 'Console siren audio enabled' : 'Audio is not supported by this browser',
      started ? 'success' : 'error',
    );
  };

  const handleOverride = () => {
    run(
      () =>
        api.override(
          {
            nodeId: override.nodeId,
            level: override.level,
            note: override.note,
            durationMinutes: Number(override.durationMinutes),
          },
          operator,
        ),
      'Risk override applied',
    ).then((result) => {
      if (result) setOverride((current) => ({ ...current, note: '' }));
    });
  };

  const handleClearOverride = (nodeId) => {
    run(() => api.clearOverride(nodeId, operator), 'Risk override removed', { closeModal: false });
  };

  const handleTestSos = () => {
    run(() => api.testSos(sosNode, operator), 'SOS channel exercised — alert created');
  };

  const handleAcknowledgeAll = () => {
    run(() => api.acknowledgeAll(operator), 'All active alerts acknowledged', { closeModal: false });
  };

  return (
    <div className="authority-console">
      <section className="panel command-hero">
        <div className="command-hero__copy">
          <span className="eyebrow">Authority control · Level 4</span>
          <h2>Emergency command</h2>
          <p>
            Commands issued here are broadcast to every connected operator and permanently written to the
            incident audit trail.
          </p>
          <div className="command-hero__status">
            <span className="status-dot status-dot--pulse" />
            <span>{operator}</span>
            <span className="command-hero__separator" />
            <span>Duty authority authenticated</span>
          </div>
        </div>
        <div className="command-hero__readout">
          <span className="micro-label">Sector condition</span>
          <RiskGauge
            score={summary?.peakRisk ?? 0}
            level={summary?.peakRiskLevel ?? 'low'}
            size="small"
            label={peakNode?.name ?? 'Regional peak'}
          />
        </div>
      </section>

      {evacuation?.active ? (
        <div className="evacuation-active">
          <span className="evacuation-active__icon">
            <Siren size={22} />
          </span>
          <div>
            <span className="eyebrow">Broadcast active</span>
            <strong>Evacuation order in effect for {evacuation.targetName}</strong>
            <p>
              {evacuation.reason} Issued by {evacuation.issuedBy} {formatRelative(evacuation.issuedAt)}.
            </p>
          </div>
          <button className="button button--dark" onClick={() => setModal('all-clear')} disabled={busy}>
            <Undo2 size={15} />
            Issue all-clear
          </button>
        </div>
      ) : null}

      <div className="command-grid">
        <section className="panel command-card command-card--primary">
          <div className="command-card__head">
            <span className="command-card__icon">
              <Megaphone size={20} />
            </span>
            <div>
              <span className="eyebrow">Primary directive</span>
              <h3>Evacuation order</h3>
            </div>
          </div>
          <p className="command-card__copy">
            Activate public sirens and push a mandatory evacuation directive to the selected sector. Use
            only when life-safety thresholds are breached.
          </p>
          <div className="command-card__facts">
            <div>
              <span className="micro-label">Target</span>
              <strong>{evacuation?.active ? evacuation.targetName : 'All sectors'}</strong>
            </div>
            <div>
              <span className="micro-label">Siren channel</span>
              <strong>{siren?.enabled ? 'Broadcasting' : 'Standby'}</strong>
            </div>
            <div>
              <span className="micro-label">Assembly points</span>
              <strong>03 mapped</strong>
            </div>
          </div>
          <button
            className="button button--danger button--large"
            onClick={() => setModal('evacuation')}
            disabled={busy || evacuation?.active}
          >
            <Siren size={18} />
            {evacuation?.active ? 'Order already active' : 'Trigger evacuation'}
          </button>
          <span className="command-card__note">
            <TriangleAlert size={12} /> Requires duty officer confirmation · logged to audit trail
          </span>
        </section>

        <section className="panel command-card">
          <div className="command-card__head">
            <span className="command-card__icon">
              {siren?.enabled ? <Volume2 size={20} /> : <VolumeX size={20} />}
            </span>
            <div>
              <span className="eyebrow">Public warning</span>
              <h3>Siren network</h3>
            </div>
          </div>
          <p className="command-card__copy">
            Toggle the physical siren relay at the central gateway. Console audio is generated locally for
            the duty officer.
          </p>
          <div className={`siren-state ${siren?.enabled ? 'siren-state--active' : ''}`}>
            <span className="siren-state__glyph">
              <Siren size={22} />
            </span>
            <div>
              <strong>{siren?.enabled ? 'Broadcast active' : 'Siren idle'}</strong>
              <span>{siren?.enabled ? 'Gateway relay closed' : 'Gateway relay open'}</span>
            </div>
            <span className="status-dot status-dot--pulse" />
          </div>
          <div className="button-row">
            <button className="button button--quiet" onClick={handleSirenToggle} disabled={busy}>
              {siren?.enabled ? <VolumeX size={15} /> : <Volume2 size={15} />}
              {siren?.enabled ? 'Silence' : 'Activate'}
            </button>
            <button className="button button--ghost" onClick={handleLocalAudio} disabled={busy}>
              {audioActive ? 'Stop local audio' : 'Local audio'}
            </button>
          </div>
        </section>

        <section className="panel command-card">
          <div className="command-card__head">
            <span className="command-card__icon">
              <ShieldAlert size={20} />
            </span>
            <div>
              <span className="eyebrow">Risk governance</span>
              <h3>Override node risk</h3>
            </div>
          </div>
          <p className="command-card__copy">
            Temporarily supersede the automated risk state while retaining the underlying sensor
            assessment for audit.
          </p>
          <div className="override-form">
            <label className="field">
              <span>Sensor node</span>
              <select
                value={override.nodeId}
                onChange={(event) => setOverride({ ...override, nodeId: event.target.value })}
              >
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.name} · {riskLabel(node.risk.level)}
                  </option>
                ))}
              </select>
            </label>
            <div className="field">
              <span>Set risk state</span>
              <div className="level-picker">
                {['low', 'moderate', 'high', 'severe'].map((level) => (
                  <button
                    key={level}
                    type="button"
                    className={`level-picker__option level-picker__option--${level} ${
                      override.level === level ? 'level-picker__option--active' : ''
                    }`}
                    onClick={() => setOverride({ ...override, level })}
                  >
                    {riskLabel(level)}
                  </button>
                ))}
              </div>
            </div>
            <label className="field">
              <span>Operator rationale</span>
              <textarea
                rows="2"
                value={override.note}
                onChange={(event) => setOverride({ ...override, note: event.target.value })}
                placeholder="Reason for overriding automated evaluation…"
              />
            </label>
            <div className="override-form__row">
              <label className="field field--compact">
                <span>Duration</span>
                <select
                  value={override.durationMinutes}
                  onChange={(event) =>
                    setOverride({ ...override, durationMinutes: Number(event.target.value) })
                  }
                >
                  <option value={30}>30 min</option>
                  <option value={60}>60 min</option>
                  <option value={120}>2 hours</option>
                  <option value={240}>4 hours</option>
                </select>
              </label>
              <button
                className="button button--primary"
                onClick={handleOverride}
                disabled={busy || override.note.trim().length < 4}
              >
                Apply override
              </button>
            </div>
          </div>
        </section>

        <section className="panel command-card">
          <div className="command-card__head">
            <span className="command-card__icon">
              <Radio size={20} />
            </span>
            <div>
              <span className="eyebrow">Rapid response</span>
              <h3>Alert operations</h3>
            </div>
          </div>
          <p className="command-card__copy">
            Clear the active warning queue or exercise a node SOS channel without waiting for hardware.
          </p>
          <div className="rapid-actions">
            <button className="button button--quiet" onClick={handleAcknowledgeAll} disabled={busy}>
              <CheckCheck size={16} />
              Acknowledge all
              <span className="button__count">{summary?.unacknowledgedAlerts ?? 0}</span>
            </button>
            <button className="button button--quiet" onClick={() => setModal('sos')} disabled={busy}>
              <Radio size={16} />
              Exercise SOS
            </button>
          </div>
          <div className="rapid-metrics">
            <div>
              <span className="micro-label">Active alerts</span>
              <strong>{summary?.activeAlerts ?? 0}</strong>
            </div>
            <div>
              <span className="micro-label">Overrides</span>
              <strong>{activeOverridesCount}</strong>
            </div>
            <div>
              <span className="micro-label">Nodes online</span>
              <strong>
                {summary?.nodesOnline ?? 0}/{summary?.nodesTotal ?? 0}
              </strong>
            </div>
          </div>
        </section>
      </div>

      <section className="panel override-register">
        <header className="panel__head">
          <div>
            <span className="eyebrow">Temporary authority state</span>
            <h2>Active overrides</h2>
          </div>
          <span className="panel__count">{overrides.length}</span>
        </header>
        {overrides.length === 0 ? (
          <p className="override-register__empty">No manual overrides active. All nodes follow automated thresholds.</p>
        ) : (
          <div className="override-register__list">
            {overrides.map((node) => (
              <div className="override-register__row" key={node.id}>
                <div>
                  <strong>{node.name}</strong>
                  <span>
                    Sensor {riskLabel(node.sensorRisk.level)} · effective {riskLabel(node.risk.level)}
                  </span>
                </div>
                <RiskBadge level={node.risk.level} />
                <p>{node.override.note}</p>
                <span className="override-register__meta">
                  {node.override.by} · until {new Date(node.override.until).toLocaleTimeString()}
                </span>
                <button
                  className="button button--quiet button--tiny"
                  onClick={() => handleClearOverride(node.id)}
                  disabled={busy}
                >
                  <Undo2 size={13} />
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {modal === 'evacuation' ? (
        <Modal
          title="Confirm evacuation order"
          eyebrow="Irreversible public broadcast"
          onClose={() => setModal(null)}
          tone="alert"
          footer={
            <>
              <button className="button button--quiet" onClick={() => setModal(null)} disabled={busy}>
                Cancel
              </button>
              <button
                className="button button--danger"
                onClick={triggerEvacuation}
                disabled={busy || evacReason.trim().length < 5}
              >
                <Siren size={16} />
                {busy ? 'Broadcasting…' : 'Broadcast evacuation'}
              </button>
            </>
          }
        >
          <div className="confirm-dialog">
            <div className="confirm-dialog__warning">
              <TriangleAlert size={20} />
              <p>
                This will activate public sirens and send a mandatory evacuation order. Confirm the target
                and rationale before proceeding.
              </p>
            </div>
            <label className="field">
              <span>Target sector</span>
              <select value={evacTarget} onChange={(event) => setEvacTarget(event.target.value)}>
                <option value="all">All sectors — Nashik Basin</option>
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.name} — {Math.round(node.risk.score)} risk
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Operational rationale</span>
              <textarea
                rows="4"
                value={evacReason}
                onChange={(event) => setEvacReason(event.target.value)}
              />
            </label>
            <div className="confirm-dialog__checklist">
              <span>Assembly points notified</span>
              <span>Public siren relay armed</span>
              <span>Incident audit record open</span>
            </div>
          </div>
        </Modal>
      ) : null}

      {modal === 'all-clear' ? (
        <Modal
          title="Issue evacuation all-clear"
          eyebrow="Return sector to monitoring"
          onClose={() => setModal(null)}
          footer={
            <>
              <button className="button button--quiet" onClick={() => setModal(null)} disabled={busy}>
                Cancel
              </button>
              <button className="button button--primary" onClick={handleAllClear} disabled={busy}>
                <Undo2 size={15} />
                {busy ? 'Closing order…' : 'Confirm all-clear'}
              </button>
            </>
          }
        >
          <div className="confirm-dialog">
            <div className="confirm-dialog__warning">
              <Undo2 size={20} />
              <p>
                The evacuation order will be resolved, sirens silenced and the sector returned to
                monitoring. Other active sensor warnings remain in force.
              </p>
            </div>
            <div className="confirm-dialog__summary">
              <span className="micro-label">Current order</span>
              <strong>{evacuation?.targetName}</strong>
              <p>{evacuation?.reason}</p>
            </div>
          </div>
        </Modal>
      ) : null}

      {modal === 'sos' ? (
        <Modal
          title="Exercise node SOS channel"
          eyebrow="Manual emergency drill"
          onClose={() => setModal(null)}
          footer={
            <>
              <button className="button button--quiet" onClick={() => setModal(null)} disabled={busy}>
                Cancel
              </button>
              <button className="button button--danger" onClick={handleTestSos} disabled={busy}>
                <Radio size={16} />
                {busy ? 'Transmitting…' : 'Trigger SOS alert'}
              </button>
            </>
          }
        >
          <div className="confirm-dialog">
            <div className="confirm-dialog__warning">
              <TriangleAlert size={20} />
              <p>
                This creates a live severe SOS alert in the dashboard, exactly as a tactile button press
                would. Use it to validate responder readiness.
              </p>
            </div>
            <label className="field">
              <span>Source node</span>
              <select value={sosNode} onChange={(event) => setSosNode(event.target.value)}>
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.name} · {node.id}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
