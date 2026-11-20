import { useState } from 'react';
import { Shield, MapPin, Navigation } from 'lucide-react';

export function PeoplePortal() {
  const [location, setLocation] = useState(null);
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(false);

  const getLocation = () => {
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        setLocation({ lat, lon });
        try {
          const res = await fetch(`/api/evacuation/safe-route?lat=${lat}&lon=${lon}`);
          const data = await res.json();
          if (data.ok) setRoute(data.data);
        } catch (e) {
          console.error(e);
        }
        setLoading(false);
      },
      (err) => {
        alert('Location access required for evacuation guidance');
        setLoading(false);
      }
    );
  };

  return (
    <div className="people-portal" style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <Shield size={48} style={{ color: '#EAAA00', margin: '0 auto' }} />
        <h1 style={{ margin: '1rem 0' }}>SENTINEL - Citizen Portal</h1>
        <p>Emergency Alerts & Safe Evacuation Routes</p>
      </div>

      <button onClick={getLocation} disabled={loading} style={{ width: '100%', padding: '1rem', background: '#EAAA00', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '1rem' }}>
        {loading ? 'Getting Location...' : 'Get My Safe Route'}
      </button>

      {route && (
        <div style={{ marginTop: '2rem', background: 'rgba(58,15,52,0.5)', padding: '1.5rem', borderRadius: '12px', border: '1px solid rgba(221,211,232,0.3)' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <MapPin size={24} /> Safest Shelter: {route.safestShelter.name}
          </h2>
          <p>Distance: {route.route.distanceKm} km | ETA: ~{route.route.estimatedTimeMin} min</p>
          
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
            <a href={route.directions.googleMaps} target="_blank" rel="noopener noreferrer" style={{ flex: 1, padding: '0.75rem', background: '#4285F4', color: 'white', textDecoration: 'none', textAlign: 'center', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
              <Navigation size={18} /> Google Maps
            </a>
            <a href={route.directions.appleMaps} target="_blank" rel="noopener noreferrer" style={{ flex: 1, padding: '0.75rem', background: '#000', color: 'white', textDecoration: 'none', textAlign: 'center', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
              <Navigation size={18} /> Apple Maps
            </a>
            <a href={route.directions.waze} target="_blank" rel="noopener noreferrer" style={{ flex: 1, padding: '0.75rem', background: '#33CCFF', color: 'white', textDecoration: 'none', textAlign: 'center', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
              <Navigation size={18} /> Waze
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
