import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import {
  ASSEMBLY_POINTS,
  CONTOURS,
  HILLS,
  LABELS,
  RESERVOIR,
  RIVER_GODAVARI,
  RIVER_TRIBUTARY,
  RISK_RADIUS_METERS,
  ROADS,
  SITE_CENTER,
  WARDS,
} from '../lib/map-data.js';
import { formatCoordinate, formatNumber, formatRelative, riskLabel } from '../lib/format.js';

const COLORS = {
  aubergine: '#3A0F34',
  silver: '#DDD3E8',
  marigold: '#EAAA00',
};

const RISK_STYLES = {
  low: { color: 'rgba(221,211,232,0.42)', fill: 'rgba(221,211,232,0.035)', weight: 1 },
  moderate: { color: 'rgba(221,211,232,0.65)', fill: 'rgba(221,211,232,0.06)', weight: 1.2 },
  high: { color: 'rgba(234,170,0,0.62)', fill: 'rgba(234,170,0,0.07)', weight: 1.4 },
  severe: { color: 'rgba(234,170,0,0.95)', fill: 'rgba(234,170,0,0.11)', weight: 1.8 },
};

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function popupHtml(node) {
  const factors = (node.risk.topFactors ?? [])
    .slice(0, 3)
    .map(
      (factor) => `
        <div class="map-popup__factor">
          <span>${escapeHtml(factor.label)}</span>
          <strong>${escapeHtml(factor.value)}</strong>
        </div>`,
    )
    .join('');

  return `
    <div class="map-popup">
      <div class="map-popup__top">
        <span class="map-popup__id">${escapeHtml(node.id)}</span>
        <span class="map-popup__risk map-popup__risk--${node.risk.level}">${riskLabel(node.risk.level)}</span>
      </div>
      <h3>${escapeHtml(node.name)}</h3>
      <p class="map-popup__location">${escapeHtml(node.location)}</p>
      <div class="map-popup__metrics">
        <div><span>Water</span><strong>${formatNumber(node.latest.waterLevel)} cm</strong></div>
        <div><span>Rain</span><strong>${formatNumber(node.latest.rain)} mm/h</strong></div>
        <div><span>AQI</span><strong>${formatNumber(node.latest.aqi, { maximumFractionDigits: 0 })}</strong></div>
        <div><span>Battery</span><strong>${node.health.batteryPercent}%</strong></div>
      </div>
      <div class="map-popup__factors">
        <span class="map-popup__section-label">Risk contributors</span>
        ${factors || '<span class="map-popup__quiet">No threshold contributors</span>'}
      </div>
      <div class="map-popup__footer">
        <span>${formatCoordinate(node.lat, 'lat')} · ${formatCoordinate(node.lon, 'lon')}</span>
        <span>${escapeHtml(formatRelative(node.health.lastSeen))}</span>
      </div>
    </div>`;
}

function baseMapLayers() {
  const layers = [];
  const add = (layer) => {
    layers.push(layer);
    return layer;
  };

  HILLS.forEach((hill) => {
    add(
      L.polygon(hill, {
        color: 'rgba(221,211,232,0.055)',
        weight: 1,
        fillColor: COLORS.silver,
        fillOpacity: 0.025,
        interactive: false,
      }),
    );
  });

  CONTOURS.forEach((contour) => {
    add(
      L.polyline(contour, {
        color: 'rgba(221,211,232,0.14)',
        weight: 0.8,
        dashArray: '2 5',
        interactive: false,
      }),
    );
  });

  WARDS.forEach((ward) => {
    add(
      L.polygon(ward.path, {
        color: 'rgba(221,211,232,0.17)',
        weight: 1,
        dashArray: '5 7',
        fillOpacity: 0,
        interactive: false,
      }),
    );
  });

  add(
    L.polyline(RIVER_GODAVARI, {
      color: 'rgba(221,211,232,0.055)',
      weight: 30,
      lineCap: 'round',
      interactive: false,
    }),
  );
  add(
    L.polyline(RIVER_GODAVARI, {
      color: 'rgba(221,211,232,0.26)',
      weight: 4,
      lineCap: 'round',
      interactive: false,
    }),
  );
  add(
    L.polyline(RIVER_TRIBUTARY, {
      color: 'rgba(221,211,232,0.2)',
      weight: 2.5,
      lineCap: 'round',
      interactive: false,
    }),
  );

  add(
    L.polygon(RESERVOIR, {
      color: 'rgba(234,170,0,0.36)',
      weight: 1,
      fillColor: COLORS.marigold,
      fillOpacity: 0.055,
      interactive: false,
    }),
  );

  ROADS.forEach((road) => {
    add(
      L.polyline(road.path, {
        color: 'rgba(221,211,232,0.08)',
        weight: road.width + 4,
        lineCap: 'round',
        interactive: false,
      }),
    );
    add(
      L.polyline(road.path, {
        color: 'rgba(221,211,232,0.32)',
        weight: road.width,
        lineCap: 'round',
        interactive: false,
      }),
    );
  });

  LABELS.forEach((label) => {
    add(
      L.marker([label.lat, label.lon], {
        interactive: false,
        icon: L.divIcon({
          className: 'map-place-label-wrap',
          html: `<span class="map-place-label map-place-label--${label.kind}">${escapeHtml(label.text)}</span>`,
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        }),
      }),
    );
  });

  ASSEMBLY_POINTS.forEach((point) => {
    add(
      L.marker([point.lat, point.lon], {
        interactive: false,
        icon: L.divIcon({
          className: 'map-assembly-wrap',
          html: `<span class="map-assembly" title="${escapeHtml(point.name)}"><span class="map-assembly__mark"></span><span class="map-assembly__label">${escapeHtml(point.name)}</span></span>`,
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        }),
      }),
    );
  });

  return layers;
}

export function InteractiveMap({
  nodes = [],
  selectedNodeId,
  onSelectNode,
  className = '',
  showControls = true,
  center = SITE_CENTER,
  bounds,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const nodeLayerRef = useRef(new Map());
  const selectRef = useRef(onSelectNode);
  const hasFocusedRef = useRef(false);
  const [pointer, setPointer] = useState(null);

  selectRef.current = onSelectNode;

  useEffect(() => {
    if (!containerRef.current) return undefined;
    if (mapRef.current) return undefined;

    try {
      const map = L.map(containerRef.current, {
        center: Array.isArray(center) ? center : SITE_CENTER,
        zoom: 13,
        zoomControl: false,
        attributionControl: false,
        minZoom: 10,
        maxZoom: 17,
        zoomSnap: 0.25,
        preferCanvas: true,
        worldCopyJump: false,
      });
      mapRef.current = map;

      const fitBounds = Array.isArray(bounds) && bounds.length === 2 ? bounds : [
        [19.974, 73.754],
        [20.068, 73.869],
      ];
      try {
        map.fitBounds(fitBounds, { padding: [20, 20] });
      } catch (e) {
        map.setView(Array.isArray(center) ? center : SITE_CENTER, 13);
      }

      if (showControls) {
        try {
          L.control.zoom({ position: 'bottomright' }).addTo(map);
          L.control.scale({ position: 'bottomleft', imperial: false, maxWidth: 110 }).addTo(map);
        } catch (e) {}
      }

      try {
        L.featureGroup(baseMapLayers()).addTo(map);
      } catch (e) {}

      map.on('mousemove', (event) => {
        setPointer({ lat: event.latlng.lat, lon: event.latlng.lng });
      });
      map.on('mouseout', () => setPointer(null));

      const observer = new ResizeObserver(() => {
        if (mapRef.current) {
          mapRef.current.invalidateSize({ pan: false });
        }
      });
      observer.observe(containerRef.current);
      setTimeout(() => {
        if (mapRef.current) mapRef.current.invalidateSize({ pan: false });
      }, 100);

      return () => {
        observer.disconnect();
        if (mapRef.current) {
          mapRef.current.remove();
          mapRef.current = null;
        }
        nodeLayerRef.current.clear();
      };
    } catch (e) {
      console.error('Map init error:', e);
      return undefined;
    }
  }, [showControls]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const currentIds = new Set(nodes.map((node) => node.id));

    for (const [nodeId, layer] of nodeLayerRef.current.entries()) {
      if (!currentIds.has(nodeId)) {
        try { layer.marker.remove(); layer.circle.remove(); } catch {}
        nodeLayerRef.current.delete(nodeId);
      }
    }

    nodes.forEach((node, index) => {
      const selected = node.id === selectedNodeId;
      const riskStyle = RISK_STYLES[node.risk?.level] ?? RISK_STYLES.low;
      const radius = (RISK_RADIUS_METERS[node.risk?.level] ?? 800) * (selected ? 1.08 : 1);
      const markerHtml = `
        <div class="map-node map-node--${node.risk?.level || 'low'} ${selected ? 'map-node--selected' : ''}">
          <span class="map-node__pulse"></span>
          <span class="map-node__ring"></span>
          <span class="map-node__core">${String(index + 1).padStart(2, '0')}</span>
          <span class="map-node__label">
            <strong>${escapeHtml(node.name)}</strong>
            <span>${Math.round(node.risk?.score || 0)} · ${riskLabel(node.risk?.level || 'low')}</span>
          </span>
        </div>`;
      const icon = L.divIcon({
        className: 'map-node-wrap',
        html: markerHtml,
        iconSize: [168, 72],
        iconAnchor: [84, 36],
      });

      let entry = nodeLayerRef.current.get(node.id);
      if (!entry) {
        const marker = L.marker([node.lat, node.lon], { icon, riseOnHover: true }).addTo(map);
        const circle = L.circle([node.lat, node.lon], {
          radius,
          color: riskStyle.color,
          weight: riskStyle.weight,
          fillColor: riskStyle.fill,
          fillOpacity: 0.8,
          opacity: 0.9,
        }).addTo(map);

        marker.on('click', () => {
          selectRef.current?.(node.id);
        });
        marker.bindPopup(popupHtml(node), {
          className: 'map-popup-pane',
          maxWidth: 320,
          closeButton: false,
        });

        entry = { marker, circle };
        nodeLayerRef.current.set(node.id, entry);
      } else {
        entry.marker.setLatLng([node.lat, node.lon]);
        entry.marker.setIcon(icon);
        entry.circle.setLatLng([node.lat, node.lon]);
        entry.circle.setRadius(radius);
        entry.circle.setStyle(riskStyle);
        entry.marker.bindPopup(popupHtml(node), {
          className: 'map-popup-pane',
          maxWidth: 320,
          closeButton: false,
        });
      }

      if (selected) {
        entry.circle.setStyle({ ...riskStyle, weight: riskStyle.weight + 0.6 });
        if (!entry.marker.isPopupOpen()) {
          entry.marker.openPopup();
        }
      } else {
        entry.circle.setStyle(riskStyle);
      }
    });
  }, [nodes, selectedNodeId]);

  useEffect(() => {
    if (!selectedNodeId || !mapRef.current || hasFocusedRef.current) return;
    const node = nodes.find((item) => item.id === selectedNodeId);
    if (!node) return;
    hasFocusedRef.current = true;
    try {
      mapRef.current.panTo([node.lat, node.lon], { animate: true, duration: 0.5 });
    } catch {}
  }, [nodes, selectedNodeId]);

  useEffect(() => {
    hasFocusedRef.current = false;
  }, [selectedNodeId]);

  return (
    <div className={`interactive-map ${className}`}>
      <div ref={containerRef} className="interactive-map__canvas" role="presentation" />
      <div className="interactive-map__hud">
        <span className="map-hud-chip">
          <span className="status-dot status-dot--pulse" /> Live GPS
        </span>
        {pointer ? (
          <span className="map-hud-chip map-hud-chip--coords">
            {formatCoordinate(pointer.lat, 'lat')} · {formatCoordinate(pointer.lon, 'lon')}
          </span>
        ) : (
          <span className="map-hud-chip">Node markers scale with composite risk</span>
        )}
      </div>
    </div>
  );
}
