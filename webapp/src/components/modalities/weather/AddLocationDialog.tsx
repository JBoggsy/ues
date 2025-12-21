/**
 * Dialog for adding a new weather location.
 * Supports address search, map selection, preset cities, and manual entry.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { MapPin, Search, Map, Building2, Edit3, Loader2, X } from 'lucide-react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { MapPicker } from '../location/MapPicker';
import { useForwardGeocoding, useReverseGeocoding } from '../location/useGeocoding';
import { WEATHER_PRESET_CITIES, type WeatherPresetCity } from './types';

interface AddLocationDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog is closed */
  onOpenChange: (open: boolean) => void;
  /** Callback when location is submitted */
  onSubmit: (latitude: number, longitude: number, name?: string) => Promise<void>;
}

interface SelectedLocation {
  latitude: number;
  longitude: number;
  displayName?: string;
}

export function AddLocationDialog({
  open,
  onOpenChange,
  onSubmit,
}: AddLocationDialogProps) {
  const [activeTab, setActiveTab] = useState<string>('search');
  const [selectedLocation, setSelectedLocation] = useState<SelectedLocation | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearchResults, setShowSearchResults] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Manual entry state
  const [manualLat, setManualLat] = useState('');
  const [manualLon, setManualLon] = useState('');
  const [manualName, setManualName] = useState('');
  const [manualErrors, setManualErrors] = useState<{ lat?: string; lon?: string }>({});

  // Geocoding hooks
  const {
    results: searchResults,
    isLoading: isSearching,
    search: searchAddress,
    clear: clearSearch,
  } = useForwardGeocoding();

  const {
    address: reverseAddress,
    isLoading: isReversing,
    lookup: lookupAddress,
    clear: clearReverse,
  } = useReverseGeocoding();

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (open) {
      setActiveTab('search');
      setSelectedLocation(null);
      setSearchQuery('');
      setShowSearchResults(false);
      setManualLat('');
      setManualLon('');
      setManualName('');
      setManualErrors({});
      clearSearch();
      clearReverse();
    }
  }, [open, clearSearch, clearReverse]);

  // Trigger search when query changes
  useEffect(() => {
    if (searchQuery.length >= 3) {
      searchAddress(searchQuery);
      setShowSearchResults(true);
    } else {
      clearSearch();
      setShowSearchResults(false);
    }
  }, [searchQuery, searchAddress, clearSearch]);

  // Update display name from reverse geocoding
  useEffect(() => {
    if (reverseAddress && selectedLocation && !selectedLocation.displayName) {
      setSelectedLocation((prev) =>
        prev ? { ...prev, displayName: reverseAddress } : null
      );
    }
  }, [reverseAddress, selectedLocation]);

  // Handle search result selection
  const handleSearchResultSelect = useCallback(
    (result: { lat: number; lon: number; displayName: string }) => {
      setSelectedLocation({
        latitude: result.lat,
        longitude: result.lon,
        displayName: result.displayName,
      });
      setSearchQuery('');
      setShowSearchResults(false);
      clearSearch();
    },
    [clearSearch]
  );

  // Handle preset city selection
  const handlePresetSelect = useCallback((city: WeatherPresetCity) => {
    setSelectedLocation({
      latitude: city.latitude,
      longitude: city.longitude,
      displayName: `${city.name}, ${city.region}`,
    });
  }, []);

  // Handle map selection
  const handleMapSelect = useCallback(
    (lat: number, lng: number) => {
      setSelectedLocation({
        latitude: lat,
        longitude: lng,
      });
      lookupAddress(lat, lng);
    },
    [lookupAddress]
  );

  // Validate and apply manual entry
  const validateManualEntry = useCallback((): boolean => {
    const errors: { lat?: string; lon?: string } = {};

    if (!manualLat.trim()) {
      errors.lat = 'Required';
    } else {
      const lat = parseFloat(manualLat);
      if (isNaN(lat) || lat < -90 || lat > 90) {
        errors.lat = 'Must be between -90 and 90';
      }
    }

    if (!manualLon.trim()) {
      errors.lon = 'Required';
    } else {
      const lon = parseFloat(manualLon);
      if (isNaN(lon) || lon < -180 || lon > 180) {
        errors.lon = 'Must be between -180 and 180';
      }
    }

    setManualErrors(errors);

    if (Object.keys(errors).length === 0) {
      const lat = parseFloat(manualLat);
      const lon = parseFloat(manualLon);
      setSelectedLocation({
        latitude: lat,
        longitude: lon,
        displayName: manualName.trim() || undefined,
      });
      lookupAddress(lat, lon);
      return true;
    }
    return false;
  }, [manualLat, manualLon, manualName, lookupAddress]);

  // Handle form submission
  const handleSubmit = useCallback(async () => {
    // For manual tab, validate first
    if (activeTab === 'manual') {
      if (!validateManualEntry()) return;
    }

    if (!selectedLocation) {
      toast.error('Please select a location first');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(
        selectedLocation.latitude,
        selectedLocation.longitude,
        selectedLocation.displayName
      );
      toast.success('Weather location added');
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to add location:', error);
      toast.error('Failed to add weather location');
    } finally {
      setIsSubmitting(false);
    }
  }, [activeTab, selectedLocation, validateManualEntry, onSubmit, onOpenChange]);

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedLocation(null);
    clearReverse();
  }, [clearReverse]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            Add Weather Location
          </DialogTitle>
          <DialogDescription>
            Add a location to track weather data. Choose how you want to specify the location.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="search" className="gap-1">
              <Search className="h-3 w-3" />
              Search
            </TabsTrigger>
            <TabsTrigger value="map" className="gap-1">
              <Map className="h-3 w-3" />
              Map
            </TabsTrigger>
            <TabsTrigger value="presets" className="gap-1">
              <Building2 className="h-3 w-3" />
              Presets
            </TabsTrigger>
            <TabsTrigger value="manual" className="gap-1">
              <Edit3 className="h-3 w-3" />
              Manual
            </TabsTrigger>
          </TabsList>

          {/* Search Tab */}
          <TabsContent value="search" className="flex-1 space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Search by City or Address</Label>
              <div className="relative">
                <Input
                  ref={searchInputRef}
                  type="text"
                  placeholder="Enter city, address, or ZIP code..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pr-8"
                />
                {isSearching && (
                  <Loader2 className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>
            </div>

            {showSearchResults && searchResults.length > 0 && (
              <div className="border rounded-md bg-background shadow-lg max-h-48 overflow-auto">
                {searchResults.map((result, index) => (
                  <button
                    key={index}
                    type="button"
                    className="w-full text-left px-3 py-2 text-sm hover:bg-muted border-b last:border-b-0 transition-colors"
                    onClick={() => handleSearchResultSelect(result)}
                  >
                    <p className="font-medium truncate">
                      {result.displayName.split(',')[0]}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {result.displayName.split(',').slice(1).join(',').trim()}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {result.lat.toFixed(4)}, {result.lon.toFixed(4)}
                    </p>
                  </button>
                ))}
              </div>
            )}

            {searchQuery.length > 0 && searchQuery.length < 3 && (
              <p className="text-xs text-muted-foreground">
                Type at least 3 characters to search...
              </p>
            )}
          </TabsContent>

          {/* Map Tab */}
          <TabsContent value="map" className="flex-1 mt-4">
            <div className="space-y-2">
              <Label>Click on the map to select a location</Label>
              <MapPicker
                initialLat={selectedLocation?.latitude}
                initialLng={selectedLocation?.longitude}
                onConfirm={handleMapSelect}
                onCancel={() => setActiveTab('search')}
              />
            </div>
          </TabsContent>

          {/* Presets Tab */}
          <TabsContent value="presets" className="flex-1 mt-4 min-h-0">
            <ScrollArea className="h-[300px]">
              <div className="space-y-4 pr-4">
                {Object.entries(WEATHER_PRESET_CITIES).map(([region, cities]) => (
                  <div key={region}>
                    <h4 className="text-sm font-medium mb-2 text-muted-foreground">
                      {region === 'North America' && '🇺🇸 '}
                      {region === 'Europe' && '🇪🇺 '}
                      {region === 'Asia-Pacific' && '🌏 '}
                      {region === 'South America' && '🌎 '}
                      {region}
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {cities.map((city) => {
                        const isSelected =
                          selectedLocation?.latitude === city.latitude &&
                          selectedLocation?.longitude === city.longitude;
                        return (
                          <Card
                            key={city.name}
                            className={cn(
                              'cursor-pointer transition-colors hover:bg-accent/50',
                              isSelected && 'border-primary bg-accent'
                            )}
                            onClick={() => handlePresetSelect(city)}
                          >
                            <CardContent className="p-2">
                              <p className="font-medium text-sm">{city.name}</p>
                              <p className="text-xs text-muted-foreground">
                                {city.latitude.toFixed(2)}, {city.longitude.toFixed(2)}
                              </p>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Manual Entry Tab */}
          <TabsContent value="manual" className="flex-1 space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="manual-lat">
                  Latitude <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="manual-lat"
                  type="number"
                  step="any"
                  min="-90"
                  max="90"
                  placeholder="e.g., 40.7128"
                  value={manualLat}
                  onChange={(e) => {
                    setManualLat(e.target.value);
                    setManualErrors((err) => ({ ...err, lat: undefined }));
                  }}
                  className={manualErrors.lat ? 'border-destructive' : ''}
                />
                {manualErrors.lat && (
                  <p className="text-xs text-destructive">{manualErrors.lat}</p>
                )}
                <p className="text-xs text-muted-foreground">Range: -90 to 90</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="manual-lon">
                  Longitude <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="manual-lon"
                  type="number"
                  step="any"
                  min="-180"
                  max="180"
                  placeholder="e.g., -74.0060"
                  value={manualLon}
                  onChange={(e) => {
                    setManualLon(e.target.value);
                    setManualErrors((err) => ({ ...err, lon: undefined }));
                  }}
                  className={manualErrors.lon ? 'border-destructive' : ''}
                />
                {manualErrors.lon && (
                  <p className="text-xs text-destructive">{manualErrors.lon}</p>
                )}
                <p className="text-xs text-muted-foreground">Range: -180 to 180</p>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="manual-name">Location Name (optional)</Label>
              <Input
                id="manual-name"
                type="text"
                placeholder="e.g., My Custom Location"
                value={manualName}
                onChange={(e) => setManualName(e.target.value)}
              />
            </div>

            <Button
              type="button"
              variant="outline"
              onClick={validateManualEntry}
              disabled={!manualLat || !manualLon}
            >
              Preview Location
            </Button>
          </TabsContent>
        </Tabs>

        {/* Selected Location Preview */}
        {selectedLocation && (
          <div className="border rounded-lg p-3 bg-muted/50 mt-4">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-2">
                <MapPin className="h-4 w-4 mt-0.5 text-primary" />
                <div>
                  <p className="font-medium">
                    {selectedLocation.displayName || 'Selected Location'}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Latitude: {selectedLocation.latitude.toFixed(4)}, Longitude:{' '}
                    {selectedLocation.longitude.toFixed(4)}
                  </p>
                  {isReversing && (
                    <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Looking up address...
                    </p>
                  )}
                </div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={clearSelection}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={
              isSubmitting ||
              (!selectedLocation && activeTab !== 'manual') ||
              (activeTab === 'manual' && (!manualLat || !manualLon))
            }
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Adding...
              </>
            ) : (
              'Add Location'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
