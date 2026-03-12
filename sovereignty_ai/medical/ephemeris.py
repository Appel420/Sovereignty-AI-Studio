"""SPICE ephemeris calculator - celestial anchor and birth synchronization."""

from typing import Tuple, Optional, Dict
from datetime import datetime
import numpy as np


class CelestialBody:
    """Represents a celestial body."""
    
    def __init__(self, name: str, mass: float, radius: float):
        self.name = name
        self.mass = mass  # kg
        self.radius = radius  # km
        self.position = np.array([0.0, 0.0, 0.0])  # km
        self.velocity = np.array([0.0, 0.0, 0.0])  # km/s


class EphemerisCalculator:
    """
    Celestial ephemeris calculator using simplified SPICE-like calculations.
    Computes positions of celestial bodies and synchronizes with birth data.
    """
    
    # Astronomical constants
    AU = 149597870.7  # Astronomical Unit in km
    G = 6.67430e-11   # Gravitational constant
    
    def __init__(self):
        """Initialize ephemeris calculator."""
        self.bodies: Dict[str, CelestialBody] = {}
        self._init_solar_system()
        self.reference_epoch = datetime(2000, 1, 1, 12, 0, 0)  # J2000
    
    def _init_solar_system(self):
        """Initialize solar system bodies with approximate data."""
        # Sun
        self.bodies['sun'] = CelestialBody('Sun', 1.989e30, 695700)
        
        # Earth
        self.bodies['earth'] = CelestialBody('Earth', 5.972e24, 6371)
        
        # Moon
        self.bodies['moon'] = CelestialBody('Moon', 7.342e22, 1737)
        
        # Other planets (simplified)
        self.bodies['mars'] = CelestialBody('Mars', 6.39e23, 3389)
        self.bodies['jupiter'] = CelestialBody('Jupiter', 1.898e27, 69911)
        self.bodies['saturn'] = CelestialBody('Saturn', 5.683e26, 58232)
    
    def julian_date(self, dt: datetime) -> float:
        """
        Convert datetime to Julian Date.
        
        Args:
            dt: Datetime object
            
        Returns:
            Julian Date
        """
        a = (14 - dt.month) // 12
        y = dt.year + 4800 - a
        m = dt.month + 12 * a - 3
        
        jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
        
        fraction = (dt.hour - 12) / 24.0 + dt.minute / 1440.0 + dt.second / 86400.0
        
        return jdn + fraction
    
    def days_since_epoch(self, dt: datetime) -> float:
        """
        Calculate days since reference epoch (J2000).
        
        Args:
            dt: Datetime object
            
        Returns:
            Days since epoch
        """
        jd = self.julian_date(dt)
        jd_epoch = self.julian_date(self.reference_epoch)
        return jd - jd_epoch
    
    def orbital_position(
        self,
        body: str,
        dt: datetime,
        simplified: bool = True
    ) -> np.ndarray:
        """
        Calculate orbital position of celestial body.
        
        Args:
            body: Name of celestial body
            dt: Datetime for calculation
            simplified: Use simplified circular orbit approximation
            
        Returns:
            Position vector [x, y, z] in km
        """
        if body not in self.bodies:
            raise ValueError(f"Unknown celestial body: {body}")
        
        days = self.days_since_epoch(dt)
        
        # Simplified circular orbit calculations
        if body == 'earth':
            # Earth's orbit around Sun
            orbital_period = 365.25  # days
            orbital_radius = self.AU  # km
            angle = 2 * np.pi * days / orbital_period
            
            x = orbital_radius * np.cos(angle)
            y = orbital_radius * np.sin(angle)
            z = 0.0
            
        elif body == 'moon':
            # Moon's orbit around Earth
            orbital_period = 27.32  # days
            orbital_radius = 384400  # km
            angle = 2 * np.pi * days / orbital_period
            
            x = orbital_radius * np.cos(angle)
            y = orbital_radius * np.sin(angle)
            z = 0.0
            
        elif body == 'mars':
            orbital_period = 687.0  # days
            orbital_radius = 1.524 * self.AU
            angle = 2 * np.pi * days / orbital_period
            
            x = orbital_radius * np.cos(angle)
            y = orbital_radius * np.sin(angle)
            z = 0.0
            
        else:
            # Default to origin for other bodies
            x, y, z = 0.0, 0.0, 0.0
        
        position = np.array([x, y, z])
        self.bodies[body].position = position
        
        return position
    
    def calculate_alignment(
        self,
        body1: str,
        body2: str,
        body3: str,
        dt: datetime
    ) -> float:
        """
        Calculate angular alignment of three celestial bodies.
        
        Args:
            body1: First body (typically observer position)
            body2: Second body (middle)
            body3: Third body
            dt: Datetime for calculation
            
        Returns:
            Alignment angle in degrees (0 = perfect alignment)
        """
        pos1 = self.orbital_position(body1, dt)
        pos2 = self.orbital_position(body2, dt)
        pos3 = self.orbital_position(body3, dt)
        
        # Vectors from body2 to body1 and body3
        v1 = pos1 - pos2
        v2 = pos3 - pos2
        
        # Calculate angle between vectors
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle_rad = np.arccos(np.clip(cos_angle, -1.0, 1.0))
        angle_deg = np.degrees(angle_rad)
        
        # Return deviation from 180° (straight line alignment)
        return abs(180.0 - angle_deg)
    
    def birth_chart_sync(
        self,
        birth_datetime: datetime,
        latitude: float,
        longitude: float
    ) -> Dict[str, any]:
        """
        Synchronize celestial positions with birth data.
        
        Args:
            birth_datetime: Birth date and time
            latitude: Birth location latitude
            longitude: Birth location longitude
            
        Returns:
            Dictionary with celestial synchronization data
        """
        # Calculate positions at birth time
        positions = {}
        for body_name in self.bodies.keys():
            positions[body_name] = self.orbital_position(body_name, birth_datetime)
        
        # Calculate Sun position (zodiac sign approximation)
        days_in_year = (birth_datetime - datetime(birth_datetime.year, 1, 1)).days
        sun_longitude = (days_in_year / 365.25) * 360.0
        
        # Calculate Moon phase
        moon_pos = positions['moon']
        earth_pos = positions['earth']
        moon_phase = np.arctan2(moon_pos[1], moon_pos[0])
        
        # Resonance calculation (7.887 Hz sync)
        # Days since epoch modulo resonance period
        resonance_period = 1.0 / 7.887  # ~0.127 days
        days = self.days_since_epoch(birth_datetime)
        resonance_phase = (days % resonance_period) / resonance_period
        
        sync_data = {
            'birth_datetime': birth_datetime.isoformat(),
            'julian_date': self.julian_date(birth_datetime),
            'days_since_epoch': days,
            'celestial_positions': {
                name: pos.tolist() for name, pos in positions.items()
            },
            'sun_longitude': sun_longitude,
            'moon_phase_rad': float(moon_phase),
            'moon_phase_deg': float(np.degrees(moon_phase)),
            'resonance_phase': resonance_phase,
            'resonance_sync': resonance_phase > 0.9 or resonance_phase < 0.1,
            'location': {
                'latitude': latitude,
                'longitude': longitude
            }
        }
        
        return sync_data
    
    def predict_alignment(
        self,
        body1: str,
        body2: str,
        body3: str,
        start_date: datetime,
        days_ahead: int = 365
    ) -> Optional[datetime]:
        """
        Predict next alignment of three celestial bodies.
        
        Args:
            body1: First body
            body2: Second body
            body3: Third body
            start_date: Start date for search
            days_ahead: Number of days to search ahead
            
        Returns:
            Datetime of next alignment, or None if not found
        """
        min_alignment = float('inf')
        best_date = None
        
        # Search daily
        for day in range(days_ahead):
            check_date = start_date + datetime.timedelta(days=day)
            alignment = self.calculate_alignment(body1, body2, body3, check_date)
            
            if alignment < min_alignment:
                min_alignment = alignment
                best_date = check_date
            
            # If alignment is very close, return immediately
            if alignment < 1.0:  # Within 1 degree
                return check_date
        
        return best_date
