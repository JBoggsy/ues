/**
 * Main Location viewer component.
 * Integrates map, current location details, history, and update dialog.
 */
import { useState, useCallback, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Plus } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/api/client';
import { useModalityState } from '@/api';
import { Button } from '@/components/ui/button';
import { CurrentLocationSection } from './CurrentLocationSection';
import { LocationHistoryList } from './LocationHistoryList';
import { UpdateLocationDialog } from './UpdateLocationDialog';
import { useSavedLocations } from './useSavedLocations';
import type { LocationState, LocationEntry, UpdateLocationRequest } from './types';

/**
 * Submit a location update to the API.
 */
async function updateLocation(request: UpdateLocationRequest): Promise<void> {
  await apiClient.post('/location/update', request);
}

export function LocationViewer() {
  const queryClient = useQueryClient();

  // Fetch location state with polling
  const {
    data: locationState,
    isLoading,
    isError,
    refetch,
    isRefetching,
  } = useModalityState<LocationState>('location', 3000);

  // Saved locations from cookies
  const {
    savedLocations,
    isLoaded: savedLocationsLoaded,
    saveLocation,
    deleteLocation,
  } = useSavedLocations();

  // UI State
  const [showHistory, setShowHistory] = useState(true);
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);

  // Invalidate queries after mutations
  const invalidateLocationState = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['environment', 'modalities', 'location'] });
  }, [queryClient]);

  // Refresh handler
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Handle location update submission
  const handleUpdateLocation = useCallback(async (request: UpdateLocationRequest) => {
    await updateLocation(request);
    toast.success('Location updated');
    invalidateLocationState();
  }, [invalidateLocationState]);

  // Handle clicking a history location (could scroll to map, zoom, etc.)
  const handleHistoryLocationSelect = useCallback((location: LocationEntry) => {
    // For now, just show a toast - could enhance to zoom map to location
    toast.info(`Selected: ${location.named_location || `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`}`);
  }, []);

  // Prepare current location for components (using flat field names from API)
  const currentLocation = useMemo(() => {
    if (locationState?.current_latitude == null || locationState?.current_longitude == null) return null;
    return {
      latitude: locationState.current_latitude,
      longitude: locationState.current_longitude,
      address: locationState.current_address ?? undefined,
      named_location: locationState.current_named_location ?? undefined,
      altitude: locationState.current_altitude ?? undefined,
      accuracy: locationState.current_accuracy ?? undefined,
      speed: locationState.current_speed ?? undefined,
      bearing: locationState.current_bearing ?? undefined,
    };
  }, [locationState]);

  // Convert current to LocationEntry for history comparison
  const currentAsEntry = useMemo((): LocationEntry | null => {
    if (locationState?.current_latitude == null || locationState?.current_longitude == null) return null;
    return {
      timestamp: locationState.last_updated,
      latitude: locationState.current_latitude,
      longitude: locationState.current_longitude,
      address: locationState.current_address ?? undefined,
      named_location: locationState.current_named_location ?? undefined,
      altitude: locationState.current_altitude ?? undefined,
      accuracy: locationState.current_accuracy ?? undefined,
      speed: locationState.current_speed ?? undefined,
      bearing: locationState.current_bearing ?? undefined,
      is_current: true,
    };
  }, [locationState]);

  // Get history from API (uses location_history field name)
  const historyLocations = useMemo(() => {
    return locationState?.location_history ?? [];
  }, [locationState]);

  // Error state
  if (isError) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive mb-4">Failed to load location state</p>
        <Button variant="outline" onClick={handleRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefetching}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
        <Button
          variant="default"
          size="sm"
          onClick={() => setUpdateDialogOpen(true)}
        >
          <Plus className="h-4 w-4 mr-2" />
          Update Location
        </Button>
      </div>

      {/* Main content - stacked layout: current location section on top, history below */}
      <div className="space-y-4">
        {/* Top section: Map + Current Location Details side-by-side */}
        <CurrentLocationSection
          locationState={locationState}
          isLoading={isLoading}
          currentLocation={currentLocation}
          historyLocations={historyLocations}
          showHistory={showHistory}
          onShowHistoryChange={setShowHistory}
          onLocationClick={handleHistoryLocationSelect}
        />

        {/* Bottom section: History */}
        <LocationHistoryList
          history={historyLocations}
          currentLocation={currentAsEntry}
          onLocationSelect={handleHistoryLocationSelect}
          maxHeight="400px"
        />
      </div>

      {/* Update Location Dialog */}
      <UpdateLocationDialog
        open={updateDialogOpen}
        onOpenChange={setUpdateDialogOpen}
        onSubmit={handleUpdateLocation}
        currentLocation={currentLocation}
        savedLocations={savedLocationsLoaded ? savedLocations : []}
        onSaveLocation={saveLocation}
        onDeleteSavedLocation={deleteLocation}
      />
    </div>
  );
}
