/**
 * Hook for geocoding using Nominatim (OpenStreetMap).
 * 
 * Nominatim is free but requires:
 * - Max 1 request per second
 * - User-Agent header identifying the application
 * - No bulk geocoding
 */
import { useState, useCallback, useRef } from 'react';

const NOMINATIM_BASE_URL = 'https://nominatim.openstreetmap.org';
const USER_AGENT = 'UES-Control-Panel/1.0';

/** Result from reverse geocoding (coordinates to address) */
export interface ReverseGeocodingResult {
  displayName: string;
  address: {
    city?: string;
    town?: string;
    village?: string;
    state?: string;
    country?: string;
    countryCode?: string;
    road?: string;
    houseNumber?: string;
    postcode?: string;
    neighbourhood?: string;
    suburb?: string;
  };
}

/** Result from forward geocoding (address to coordinates) */
export interface ForwardGeocodingResult {
  lat: number;
  lon: number;
  displayName: string;
  type: string;
  importance: number;
}

/**
 * Reverse geocode coordinates to an address.
 */
export async function reverseGeocode(
  lat: number,
  lng: number
): Promise<ReverseGeocodingResult | null> {
  try {
    const response = await fetch(
      `${NOMINATIM_BASE_URL}/reverse?format=json&lat=${lat}&lon=${lng}&addressdetails=1`,
      {
        headers: {
          'User-Agent': USER_AGENT,
        },
      }
    );

    if (!response.ok) {
      console.error('Reverse geocoding failed:', response.status);
      return null;
    }

    const data = await response.json();
    
    if (data.error) {
      console.error('Reverse geocoding error:', data.error);
      return null;
    }

    return {
      displayName: data.display_name,
      address: {
        city: data.address?.city,
        town: data.address?.town,
        village: data.address?.village,
        state: data.address?.state,
        country: data.address?.country,
        countryCode: data.address?.country_code,
        road: data.address?.road,
        houseNumber: data.address?.house_number,
        postcode: data.address?.postcode,
        neighbourhood: data.address?.neighbourhood,
        suburb: data.address?.suburb,
      },
    };
  } catch (error) {
    console.error('Reverse geocoding error:', error);
    return null;
  }
}

/**
 * Forward geocode an address to coordinates.
 */
export async function forwardGeocode(
  query: string,
  limit: number = 5
): Promise<ForwardGeocodingResult[]> {
  try {
    const response = await fetch(
      `${NOMINATIM_BASE_URL}/search?format=json&q=${encodeURIComponent(query)}&limit=${limit}&addressdetails=1`,
      {
        headers: {
          'User-Agent': USER_AGENT,
        },
      }
    );

    if (!response.ok) {
      console.error('Forward geocoding failed:', response.status);
      return [];
    }

    const data = await response.json();

    return data.map((item: Record<string, unknown>) => ({
      lat: parseFloat(item.lat as string),
      lon: parseFloat(item.lon as string),
      displayName: item.display_name as string,
      type: item.type as string,
      importance: item.importance as number,
    }));
  } catch (error) {
    console.error('Forward geocoding error:', error);
    return [];
  }
}

/**
 * Get a short location name from reverse geocoding result.
 */
export function getShortLocationName(result: ReverseGeocodingResult): string {
  const { address } = result;
  const city = address.city || address.town || address.village;
  const country = address.country;
  
  if (city && country) {
    return `${city}, ${country}`;
  }
  if (address.state && country) {
    return `${address.state}, ${country}`;
  }
  if (country) {
    return country;
  }
  
  // Fallback: use first two parts of display name
  const parts = result.displayName.split(', ');
  return parts.slice(0, 2).join(', ');
}

/**
 * Hook for reverse geocoding with debouncing and caching.
 */
export function useReverseGeocoding() {
  const [address, setAddress] = useState<string | null>(null);
  const [fullResult, setFullResult] = useState<ReverseGeocodingResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastRequestRef = useRef<{ lat: number; lng: number } | null>(null);
  const cacheRef = useRef<Map<string, ReverseGeocodingResult>>(new Map());

  const lookup = useCallback(async (lat: number, lng: number) => {
    // Round to 4 decimal places for caching (about 11m precision)
    const roundedLat = Math.round(lat * 10000) / 10000;
    const roundedLng = Math.round(lng * 10000) / 10000;
    const cacheKey = `${roundedLat},${roundedLng}`;

    // Check cache first
    const cached = cacheRef.current.get(cacheKey);
    if (cached) {
      setFullResult(cached);
      setAddress(getShortLocationName(cached));
      return;
    }

    // Skip if same location is already being looked up
    if (
      lastRequestRef.current?.lat === roundedLat &&
      lastRequestRef.current?.lng === roundedLng
    ) {
      return;
    }

    lastRequestRef.current = { lat: roundedLat, lng: roundedLng };
    setIsLoading(true);
    setError(null);

    const result = await reverseGeocode(lat, lng);
    
    if (result) {
      cacheRef.current.set(cacheKey, result);
      setFullResult(result);
      setAddress(getShortLocationName(result));
    } else {
      setError('Could not resolve address');
      setAddress(null);
      setFullResult(null);
    }
    
    setIsLoading(false);
  }, []);

  const clear = useCallback(() => {
    setAddress(null);
    setFullResult(null);
    setError(null);
    lastRequestRef.current = null;
  }, []);

  return { address, fullResult, isLoading, error, lookup, clear };
}

/**
 * Hook for forward geocoding (address search) with debouncing.
 */
export function useForwardGeocoding() {
  const [results, setResults] = useState<ForwardGeocodingResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback(async (query: string) => {
    // Clear previous debounce
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    // Don't search if query is too short
    if (query.length < 3) {
      setResults([]);
      return;
    }

    // Debounce to respect rate limits
    debounceRef.current = setTimeout(async () => {
      setIsLoading(true);
      setError(null);

      const searchResults = await forwardGeocode(query);
      
      if (searchResults.length > 0) {
        setResults(searchResults);
      } else {
        setResults([]);
        setError('No results found');
      }
      
      setIsLoading(false);
    }, 500); // 500ms debounce
  }, []);

  const clear = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    setResults([]);
    setError(null);
  }, []);

  return { results, isLoading, error, search, clear };
}
