import { useDeferredValue, useEffect, useState } from 'react';
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Download,
  FileSearch,
  Filter,
  RefreshCw,
  RotateCcw,
  Search,
} from 'lucide-react';
import { api, incidentExportUrl } from '../lib/api.js';
import {
  formatDateTime,
  formatRelative,
  incidentTypeLabel,
  riskLabel,
  sourceLabel,
} from '../lib/format.js';
import { Modal } from './Modal.jsx';
import { RiskBadge } from './RiskBadge.jsx';

const PAGE_SIZE = 10;
const STATUS_OPTIONS = ['open', 'monitoring', 'acknowledged', 'resolved'];
const TYPE_OPTIONS = ['alert', 'sensor', 'sos', 'command', 'acknowledgement', 'gateway', 'evacuation', 'drill'];
const SOURCE_OPTIONS = ['automated', 'sensor', 'operator', 'system', 'hardware', 'simulator'];

const EMPTY_FILTERS = {
  search: '',
  severity: 'all',
  type: 'all',
  status: 'all',
  source: 'all',
};

export function IncidentTable({ refreshToken, onToast }) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const deferredSearch = useDeferredValue(filters.search);
  const [page, setPage] = useState(0);
  const [result, setResult] = useState({ incidents: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  const query = {
    ...filters,
    search: deferredSearch,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  };

  const load = async () => {
    setLoading(true);
    try {
      const response = await api.incidents(query);
      setResult({ incidents: response.incidents, total: response.total });
      if (response.incidents.length === 0 && page > 0) setPage(0);
    } catch (error) {
      onToast?.(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [deferredSearch, filters.severity, filters.type, filters.status, filters.source, page, refreshToken]);

  const totalPages = Math.max(1, Math.ceil(result.total / PAGE_SIZE));
  const filtersActive = Object.entries(filters).some(([key, value]) => value !== EMPTY_FILTERS[key]);
  const exportHref = incidentExportUrl({ ...filters, search: deferredSearch });

  const updateFilter = (key, value) => {
    setPage(0);
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const resetFilters = () => {
    setPage(0);
    setFilters(EMPTY_FILTERS);
  };

  return (
    <section className="panel incident-panel">
      <header className="panel__head incident-panel__head">
        <div>
          <span className="eyebrow">Operational archive</span>
          <h2>
            Incident log
            <span className="panel__count">{result.total}</span>
          </h2>
        </div>
        <div className="incident-panel__head-actions">
          <span className="live-label">
            <span className="status-dot status-dot--pulse" />
            Synced
          </span>
          <a className="button button--quiet button--small" href={exportHref} download>
            <Download size={14} />
            Export CSV
          </a>
        </div>
      </header>

      <div className="filter-bar">
        <label className="filter-search">
          <Search size={15} />
          <input
            value={filters.search}
            onChange={(event) => updateFilter('search', event.target.value)}
            placeholder="Search warnings, nodes, details…"
            aria-label="Search incidents"
          />
          {filters.search ? (
            <button
              className="filter-search__clear"
              onClick={() => updateFilter('search', '')}
              aria-label="Clear search"
            >
              ×
            </button>
          ) : null}
        </label>

        <label className="select-field">
          <span>Severity</span>
          <select value={filters.severity} onChange={(event) => updateFilter('severity', event.target.value)}>
            <option value="all">All levels</option>
            {['low', 'moderate', 'high', 'severe'].map((level) => (
              <option key={level} value={level}>
                {riskLabel(level)}
              </option>
            ))}
          </select>
        </label>

        <label className="select-field">
          <span>Event</span>
          <select value={filters.type} onChange={(event) => updateFilter('type', event.target.value)}>
            <option value="all">All events</option>
            {TYPE_OPTIONS.map((type) => (
              <option key={type} value={type}>
                {incidentTypeLabel(type)}
              </option>
            ))}
          </select>
        </label>

        <label className="select-field">
          <span>Status</span>
          <select value={filters.status} onChange={(event) => updateFilter('status', event.target.value)}>
            <option value="all">Any status</option>
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status[0].toUpperCase() + status.slice(1)}
              </option>
            ))}
          </select>
        </label>

        <label className="select-field select-field--source">
          <span>Source</span>
          <select value={filters.source} onChange={(event) => updateFilter('source', event.target.value)}>
            <option value="all">Any source</option>
            {SOURCE_OPTIONS.map((source) => (
              <option key={source} value={source}>
                {sourceLabel(source)}
              </option>
            ))}
          </select>
        </label>

        <div className="filter-bar__actions">
          <button className="icon-button filter-reset" onClick={load} aria-label="Refresh incidents">
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
          </button>
          <button
            className="icon-button filter-reset"
            onClick={resetFilters}
            aria-label="Reset filters"
            disabled={!filtersActive}
          >
            <RotateCcw size={15} />
          </button>
        </div>
      </div>

      <div className="incident-table-wrap">
        <table className="incident-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Event</th>
              <th>Node / area</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Source</th>
              <th>Status</th>
              <th aria-label="Open" />
            </tr>
          </thead>
          <tbody>
            {loading && result.incidents.length === 0 ? (
              Array.from({ length: 6 }).map((_, index) => (
                <tr className="incident-table__skeleton" key={index}>
                  <td colSpan="8">
                    <span />
                  </td>
                </tr>
              ))
            ) : null}

            {!loading && result.incidents.length === 0 ? (
              <tr>
                <td colSpan="8">
                  <div className="empty-state">
                    <span className="empty-state__icon">
                      <FileSearch size={21} />
                    </span>
                    <div>
                      <strong>No matching incidents</strong>
                      <p>Adjust the filters or clear the search to inspect the full operational record.</p>
                      {filtersActive ? (
                        <button className="button button--quiet button--tiny" onClick={resetFilters}>
                          <Filter size={13} />
                          Clear filters
                        </button>
                      ) : null}
                    </div>
                  </div>
                </td>
              </tr>
            ) : null}

            {result.incidents.map((incident) => (
              <tr key={incident.id} onClick={() => setSelected(incident)} tabIndex={0} onKeyDown={(event) => event.key === 'Enter' && setSelected(incident)}>
                <td>
                  <span className="incident-table__time">{formatDateTime(incident.createdAt)}</span>
                  <span className="incident-table__relative">{formatRelative(incident.createdAt)}</span>
                </td>
                <td>
                  <span className="incident-table__title">{incident.title}</span>
                  <span className="incident-table__detail">{incident.detail}</span>
                </td>
                <td>
                  <span className="incident-table__node">{incident.nodeName ?? 'Regional'}</span>
                  <span className="incident-table__node-id">{incident.nodeId ?? 'COMMAND'}</span>
                </td>
                <td>
                  <span className="type-pill">{incidentTypeLabel(incident.type)}</span>
                </td>
                <td>
                  <RiskBadge level={incident.severity} compact />
                </td>
                <td>
                  <span className="incident-table__source">{sourceLabel(incident.source)}</span>
                </td>
                <td>
                  <span className={`status-pill status-pill--${incident.status}`}>{incident.status}</span>
                </td>
                <td>
                  <button
                    className="incident-table__open icon-button"
                    aria-label={`Open incident ${incident.id}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      setSelected(incident);
                    }}
                  >
                    <ArrowUpRight size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <footer className="incident-panel__foot">
        <span>
          Showing {result.incidents.length ? page * PAGE_SIZE + 1 : 0}–
          {Math.min((page + 1) * PAGE_SIZE, result.total)} of {result.total} events
        </span>
        <div className="pagination">
          <button
            className="icon-button"
            onClick={() => setPage((current) => Math.max(0, current - 1))}
            disabled={page === 0}
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="pagination__label">
            PAGE {String(page + 1).padStart(2, '0')} / {String(totalPages).padStart(2, '0')}
          </span>
          <button
            className="icon-button"
            onClick={() => setPage((current) => Math.min(totalPages - 1, current + 1))}
            disabled={page >= totalPages - 1}
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </footer>

      {selected ? (
        <Modal
          title={selected.title}
          eyebrow={`${incidentTypeLabel(selected.type)} · ${formatDateTime(selected.createdAt)}`}
          onClose={() => setSelected(null)}
          size="medium"
          footer={
            <button className="button button--primary" onClick={() => setSelected(null)}>
              Close record
            </button>
          }
        >
          <div className="incident-detail">
            <div className="incident-detail__meta">
              <div>
                <span className="micro-label">Severity</span>
                <RiskBadge level={selected.severity} />
              </div>
              <div>
                <span className="micro-label">Status</span>
                <span className={`status-pill status-pill--${selected.status}`}>{selected.status}</span>
              </div>
              <div>
                <span className="micro-label">Source</span>
                <span className="incident-detail__value">{sourceLabel(selected.source)}</span>
              </div>
              <div>
                <span className="micro-label">Node</span>
                <span className="incident-detail__value">{selected.nodeName ?? 'Regional'}</span>
              </div>
            </div>
            <div className="incident-detail__section">
              <span className="micro-label">Event description</span>
              <p>{selected.detail}</p>
            </div>
            <div className="incident-detail__section">
              <span className="micro-label">Record identifier</span>
              <code>{selected.id}</code>
            </div>
            {selected.metadata && Object.keys(selected.metadata).length ? (
              <div className="incident-detail__section">
                <span className="micro-label">Machine metadata</span>
                <pre>{JSON.stringify(selected.metadata, null, 2)}</pre>
              </div>
            ) : null}
          </div>
        </Modal>
      ) : null}
    </section>
  );
}
