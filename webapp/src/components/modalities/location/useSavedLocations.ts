/**
 * Custom hook for managing saved locations in cookies.
 * Provides persistence for user-defined named locations until
 * backend support is implemented.
 */
import { useState, useEffect, useCallback } from 'react';
import type { SavedLocation } from './types';

const COOKIE_NAME = 'ues_saved_locations';
const COOKIE_MAX_AGE = 365 * 24 * 60 * 60; // 1 year in seconds

/**
 * Parse saved locations from cookie string.
 */
function parseCookie(): SavedLocation[] {
  try {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === COOKIE_NAME && value) {
        return JSON.parse(decodeURIComponent(value));
      }
    }
  } catch (error) {
    console.warn('Failed to parse saved locations cookie:', error);
  }
  return [];
}

/**
 * Save locations to cookie.
 */
function saveToCookie(locations: SavedLocation[]): void {
  const value = encodeURIComponent(JSON.stringify(locations));
  document.cookie = `${COOKIE_NAME}=${value}; max-age=${COOKIE_MAX_AGE}; path=/; SameSite=Lax`;
}

/**
 * Generate a unique ID for a saved location.
 */
function generateId(): string {
  return `loc_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Hook for managing saved/named locations with cookie persistence.
 * 
 * @returns Object with saved locations array and CRUD operations.
 */
export function useSavedLocations() {
  const [savedLocations, setSavedLocations] = useState<SavedLocation[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load from cookie on mount
  useEffect(() => {
    const locations = parseCookie();
    setSavedLocations(locations);
    setIsLoaded(true);
  }, []);

  // Save a new location
  const saveLocation = useCallback((
    name: string,
    latitude: number,
    longitude: number,
    address?: string,
    altitude?: number
  ): SavedLocation => {
    const newLocation: SavedLocation = {
      id: generateId(),
      name,
      latitude,
      longitude,
      address,
      altitude,
    };

    setSavedLocations((prev) => {
      const updated = [...prev, newLocation];
      saveToCookie(updated);
      return updated;
    });

    return newLocation;
  }, []);

  // Update an existing location
  const updateLocation = useCallback((id: string, updates: Partial<Omit<SavedLocation, 'id'>>): void => {
    setSavedLocations((prev) => {
      const updated = prev.map((loc) =>
        loc.id === id ? { ...loc, ...updates } : loc
      );
      saveToCookie(updated);
      return updated;
    });
  }, []);

  // Delete a location
  const deleteLocation = useCallback((id: string): void => {
    setSavedLocations((prev) => {
      const updated = prev.filter((loc) => loc.id !== id);
      saveToCookie(updated);
      return updated;
    });
  }, []);

  // Find a location by name (case-insensitive)
  const findByName = useCallback((name: string): SavedLocation | undefined => {
    return savedLocations.find(
      (loc) => loc.name.toLowerCase() === name.toLowerCase()
    );
  }, [savedLocations]);

  // Check if a name already exists
  const nameExists = useCallback((name: string, excludeId?: string): boolean => {
    return savedLocations.some(
      (loc) => loc.name.toLowerCase() === name.toLowerCase() && loc.id !== excludeId
    );
  }, [savedLocations]);

  return {
    savedLocations,
    isLoaded,
    saveLocation,
    updateLocation,
    deleteLocation,
    findByName,
    nameExists,
  };
}
