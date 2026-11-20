import { RadioTower, ShieldCheck, Siren, Users } from 'lucide-react';
import { AuthorityConsole } from '../components/AuthorityConsole.jsx';
import { NodeHealth } from '../components/NodeHealth.jsx';
import { riskLabel } from '../lib/format.js';

export function CommandView({ snapshot, operator, onInspect, onToast }) {
  const { summary, system, nodes, gateway } = snapshot;
  const evacuation = system?.evacuation;

  return (
    <div className="view-stack command-view">
      <div className="view-lead">
        <div>
          <span className="eyebrow">{snapshot.meta.site.code} · authority mode</span>
          <h2>Emergency command console</h2>
          <p>
            Acting operator <strong>{operator}</strong> · sector condition{' '}
            <strong>{riskLabel(summary.peakRiskLevel)}</strong> · emergency line{' '}
            <strong>{snapshot.meta.emergencyNumber}</strong>
          </p>
        </div>
        <div className="command-status-strip">
          <div>
            <span className="micro-label">Evacuation</span>
            <strong className={evacuation?.active ? 'command-status-strip__alert' : ''}>
              {evacuation?.active ? 'Active' : 'Standby'}
            </strong>
          </div>
          <div>
            <span className="micro-label">Siren relay</span>
            <strong className={system?.siren?.enabled ? 'command-status-strip__alert' : ''}>
              {system?.siren?.enabled ? 'Broadcasting' : 'Idle'}
            </strong>
          </div>
          <div>
            <span className="micro-label">Gateway</span>
            <strong>{gateway?.online ? 'Linked' : 'Offline'}</strong>
          </div>
        </div>
      </div>

      <div className="command-assurance">
        <span>
          <ShieldCheck size={15} />
          Two-step confirmation on every public broadcast
        </span>
        <span>
          <Siren size={15} />
          Siren and all-clear are audited commands
        </span>
        <span>
          <Users size={15} />
          {summary.affectedPopulation.toLocaleString('en-IN')} residents inside affected sectors
        </span>
        <span>
          <RadioTower size={15} />
          {summary.nodesOnline}/{summary.nodesTotal} sensor nodes online
        </span>
      </div>

      <AuthorityConsole
        nodes={nodes}
        system={system}
        summary={summary}
        operator={operator}
        onToast={onToast}
      />

      <NodeHealth nodes={nodes} gateway={gateway} onInspect={onInspect} />
    </div>
  );
}
