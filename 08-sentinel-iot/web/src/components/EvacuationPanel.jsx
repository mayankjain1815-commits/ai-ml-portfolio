import { useState, useEffect } from 'react';
import { Navigation, MapPin, AlertTriangle, Download, WifiOff } from 'lucide-react';

function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

export function EvacuationPanel() {
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(false);
  const [offline, setOffline] = useState(!navigator.onLine);
  const [kitDownloaded, setKitDownloaded] = useState(false);

  useEffect(() => {
    const handleOnline = () => setOffline(false);
    const handleOffline = () => setOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    if (localStorage.getItem('sentinel_offline_kit')) {
      setKitDownloaded(true);
    }
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const downloadOfflineKit = async () => {
    try {
      const res = await fetch('/api/evacuation/offline-kit');
      const data = await res.json();
      if (data.ok) {
        localStorage.setItem('sentinel_offline_kit', JSON.stringify(data.data));
        setKitDownloaded(true);
        alert('Offline evacuation kit downloaded! Works without internet.');
      }
    } catch (e) {
      alert('Failed to download offline kit');
    }
  };

  const getEvacuationRoute = () => {
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        
        try {
          if (!offline) {
            const res = await fetch(`/api/evacuation/emergency-directions?lat=${lat}&lon=${lon}`);
            const data = await res.json();
            if (data.ok) {
              setRoute(data.data);
              setLoading(false);
              return;
            }
          }
        } catch (e) {
          console.log('Falling back to offline mode');
        }
        
        // Offline mode
        const kit = localStorage.getItem('sentinel_offline_kit');
        if (!kit) {
          alert('No offline kit downloaded. Please download it while online.');
          setLoading(false);
          return;
        }
        
        const offlineData = JSON.parse(kit);
        const shelters = offlineData.shelters.map(s => ({
          ...s,
          dist: haversine(lat, lon, s.lat, s.lon)
        })).sort((a,b) => a.dist - b.dist);
        
        const safest = shelters[0];
        const distKm = safest.dist.toFixed(2);
        const timeMin = Math.round(safest.dist * 2); // rough estimate
        
        setRoute({
          safestShelter: safest,
          estimatedTime: timeMin + ' min',
          directions: {
            googleMaps: `https://www.google.com/maps/dir/?api=1&origin=${lat},${lon}&destination=${safest.lat},${safest.lon}&travelmode=driving`,
            appleMaps: `http://maps.apple.com/?saddr=${lat},${lon}&daddr=${safest.lat},${safest.lon}&dirflg=d`,
            waze: `https://waze.com/ul?ll=${safest.lat},${safest.lon}&from=${lat},${lon}&navigate=yes`,
            osm: `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${lat}%2C${lon}%3B${safest.lat}%2C${safest.lon}`
          },
          instructions: offlineData.instructions,
          offline: true,
          distance: distKm + ' km'
        });
        setLoading(false);
      },
      () => { alert('Location required for evacuation route'); setLoading(false); }
    );
  };

  return (
    <div className="evacuation-panel" style={{ background: 'linear-gradient(135deg, rgba(234,170,0,0.2), rgba(58,15,52,0.5))', padding: '1.5rem', borderRadius: '12px', border: '2px solid #EAAA00' }}>
      <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#EAAA00', margin: '0 0 1rem 0' }}>
        <AlertTriangle size={24} /> EVACUATION - SAFEST ROUTE
        {offline && <WifiOff size={16} style={{ marginLeft: 'auto', color: '#ff6b6b' }} />}
      </h3>
      
      {!kitDownloaded && !offline && (
        <button onClick={downloadOfflineKit} style={{ width: '100%', padding: '0.5rem', background: 'rgba(221,211,232,0.2)', border: '1px solid rgba(221,211,232,0.4)', borderRadius: '6px', cursor: 'pointer', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
          <Download size={16} /> Download Offline Kit (For No-Internet Use)
        </button>
      )}
      
      {kitDownloaded && (
        <div style={{ fontSize: '0.75rem', color: '#90EE90', marginBottom: '0.75rem', textAlign: 'center' }}>
          ✓ Offline kit ready
        </div>
      )}
      
      <button onClick={getEvacuationRoute} disabled={loading} style={{ width: '100%', padding: '0.75rem', background: '#EAAA00', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
        {loading ? 'FINDING SAFEST ROUTE...' : offline ? 'GET ROUTE (OFFLINE)' : 'GET SAFEST EVACUATION ROUTE'}
      </button>
      
      {route && (
        <div style={{ marginTop: '1rem' }}>
          {route.offline && <div style={{ background: 'rgba(255,107,107,0.2)', padding: '0.5rem', borderRadius: '6px', marginBottom: '0.5rem', fontSize: '0.875rem' }}>⚠️ Using offline data</div>}
          <p style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><MapPin size={16} /> To: {route.safestShelter.name}</p>
          <p>Distance: {route.distance} | ETA: {route.estimatedTime}</p>
          {route.safestShelter.contact && <p style={{ fontSize: '0.875rem' }}>Contact: {route.safestShelter.contact}</p>}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.75rem' }}>
            <a href={route.directions.googleMaps} target="_blank" rel="noopener" style={{ padding: '0.5rem', background: '#4285F4', color: 'white', textDecoration: 'none', textAlign: 'center', borderRadius: '6px' }}>
              <Navigation size={14} /> Open in Google Maps
            </a>
            <a href={route.directions.appleMaps} target="_blank" rel="noopener" style={{ padding: '0.5rem', background: '#000', color: 'white', textDecoration: 'none', textAlign: 'center', borderRadius: '6px' }}>
              <Navigation size={14} /> Open in Apple Maps
            </a>
            <a href={route.directions.waze} target="_blank" rel="noopener" style={{ padding: '0.5rem', background: '#33CCFF', color: 'white', textDecoration: 'none', textAlign: 'center', borderRadius: '6px' }}>
              <Navigation size={14} /> Open in Waze
            </a>
            <a href={route.directions.osm} target="_blank" rel="noopener" style={{ padding: '0.5rem', background: '#7EBC6F', color: 'white', textDecoration: 'none', textAlign: 'center', borderRadius: '6px' }}>
              <Navigation size={14} /> Open in OpenStreetMap
            </a>
          </div>
          <ul style={{ marginTop: '0.75rem', paddingLeft: '1.25rem', fontSize: '0.875rem' }}>
            {route.instructions?.map((i, idx) => <li key={idx}>{i}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}
