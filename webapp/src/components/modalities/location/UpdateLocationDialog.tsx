/**
 * Dialog for updating the user's location.
 * Supports manual coordinate entry, preset cities, saved locations,
 * map-based selection, and optional motion data.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { MapPin, Plus, Trash2, Navigation, Save, Map, Search, Loader2 } from 'lucide-react';
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
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { MapPicker } from './MapPicker';
import { useForwardGeocoding, useReverseGeocoding } from './useGeocoding';
import type { SavedLocation, UpdateLocationRequest } from './types';
import { PRESET_CITIES } from './types';

/**
 * A contact's postal address entry for quick location selection.
 */
export interface ContactAddressEntry {
  contact_id: string;
  display_name: string;
  label: string | null;
  address_oneline: string;
  latitude?: number;
  longitude?: number;
}

interface UpdateLocationDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog is closed */
  onOpenChange: (open: boolean) => void;
  /** Callback when location is submitted */
  onSubmit: (request: UpdateLocationRequest) => Promise<void>;
  /** Current location for pre-populating fields */
  currentLocation?: {
    latitude?: number;
    longitude?: number;
    address?: string;
    named_location?: string;
    altitude?: number;
    accuracy?: number;
    speed?: number;
    bearing?: number;
  } | null;
  /** Saved locations from cookies */
  savedLocations: SavedLocation[];
  /** Callback to save current location */
  onSaveLocation: (
    name: string,
    latitude: number,
    longitude: number,
    address?: string,
    altitude?: number
  ) => void;
  /** Callback to delete a saved location */
  onDeleteSavedLocation: (id: string) => void;
  /** Contact postal addresses for quick location selection. */
  contactAddresses?: ContactAddressEntry[];
}

/**
 * Form state for location update.
 */
interface FormState {
  latitude: string;
  longitude: string;
  address: string;
  namedLocation: string;
  altitude: string;
  accuracy: string;
  speed: string;
  bearing: string;
}

const DEFAULT_FORM_STATE: FormState = {
  latitude: '',
  longitude: '',
  address: '',
  namedLocation: '',
  altitude: '',
  accuracy: '',
  speed: '',
  bearing: '',
};

export function UpdateLocationDialog({
  open,
  onOpenChange,
  onSubmit,
  currentLocation,
  savedLocations,
  onSaveLocation,
  onDeleteSavedLocation,
  contactAddresses = [],
}: UpdateLocationDialogProps) {
  const [form, setForm] = useState<FormState>(DEFAULT_FORM_STATE);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [showMapPicker, setShowMapPicker] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  
  // Address search state
  const [addressSearch, setAddressSearch] = useState('');
  const [showSearchResults, setShowSearchResults] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  
  // Geocoding hooks
  const { results: searchResults, isLoading: isSearching, search: searchAddress, clear: clearSearch } = useForwardGeocoding();
  const { address: reverseAddress, isLoading: _isReversing, lookup: lookupAddress, clear: clearReverse } = useReverseGeocoding();

  // Pre-populate form when opening
  useEffect(() => {
    if (open && currentLocation) {
      setForm({
        latitude: currentLocation.latitude?.toString() ?? '',
        longitude: currentLocation.longitude?.toString() ?? '',
        address: currentLocation.address ?? '',
        namedLocation: currentLocation.named_location ?? '',
        altitude: currentLocation.altitude?.toString() ?? '',
        accuracy: currentLocation.accuracy?.toString() ?? '',
        speed: currentLocation.speed?.toString() ?? '',
        bearing: currentLocation.bearing?.toString() ?? '',
      });
    } else if (open) {
      setForm(DEFAULT_FORM_STATE);
    }
    setErrors({});
    setAddressSearch('');
    setShowSearchResults(false);
    clearSearch();
    clearReverse();
  }, [open, currentLocation, clearSearch, clearReverse]);
  
  // Trigger address search when typing
  useEffect(() => {
    if (addressSearch.length >= 3) {
      searchAddress(addressSearch);
      setShowSearchResults(true);
    } else {
      clearSearch();
      setShowSearchResults(false);
    }
  }, [addressSearch, searchAddress, clearSearch]);

  // Update a form field
  const updateField = useCallback((field: keyof FormState, value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => ({ ...e, [field]: undefined }));
  }, []);

  // Apply a saved or preset location
  const applyLocation = useCallback((location: { latitude: number; longitude: number; address?: string; name?: string; altitude?: number }) => {
    setForm((f) => ({
      ...f,
      latitude: location.latitude.toString(),
      longitude: location.longitude.toString(),
      address: location.address ?? '',
      namedLocation: location.name ?? '',
      altitude: location.altitude?.toString() ?? '',
    }));
    setErrors({});
  }, []);

  // Apply a preset city
  const applyPresetCity = useCallback((cityName: string) => {
    const city = PRESET_CITIES.find((c) => c.name === cityName);
    if (city) {
      applyLocation({
        latitude: city.latitude,
        longitude: city.longitude,
        address: `${city.name}, ${city.country}`,
      });
    }
  }, [applyLocation]);

  // Apply coordinates from map picker
  const applyMapSelection = useCallback((lat: number, lng: number) => {
    setForm((f) => ({
      ...f,
      latitude: lat.toFixed(6),
      longitude: lng.toFixed(6),
    }));
    setErrors({});
    setShowMapPicker(false);
    lookupAddress(lat, lng); // Look up address for selected coordinates
    toast.success('Coordinates selected from map');
  }, [lookupAddress]);
  
  // Apply address from reverse geocoding when it resolves
  useEffect(() => {
    if (reverseAddress && form.latitude && form.longitude && !form.address) {
      setForm((f) => ({ ...f, address: reverseAddress }));
    }
  }, [reverseAddress, form.latitude, form.longitude, form.address]);
  
  // Apply a search result
  const applySearchResult = useCallback((result: { lat: number; lon: number; displayName: string }) => {
    setForm((f) => ({
      ...f,
      latitude: result.lat.toFixed(6),
      longitude: result.lon.toFixed(6),
      address: result.displayName,
    }));
    setErrors({});
    setAddressSearch('');
    setShowSearchResults(false);
    clearSearch();
    toast.success('Location found');
  }, [clearSearch]);

  // Apply a saved location
  const applySavedLocation = useCallback((saved: SavedLocation) => {
    applyLocation({
      latitude: saved.latitude,
      longitude: saved.longitude,
      address: saved.address,
      name: saved.name,
      altitude: saved.altitude,
    });
  }, [applyLocation]);

  // Validate the form
  const validate = useCallback((): boolean => {
    const newErrors: Partial<Record<keyof FormState, string>> = {};
    
    // Required fields
    if (!form.latitude.trim()) {
      newErrors.latitude = 'Required';
    } else {
      const lat = parseFloat(form.latitude);
      if (isNaN(lat) || lat < -90 || lat > 90) {
        newErrors.latitude = 'Must be between -90 and 90';
      }
    }
    
    if (!form.longitude.trim()) {
      newErrors.longitude = 'Required';
    } else {
      const lng = parseFloat(form.longitude);
      if (isNaN(lng) || lng < -180 || lng > 180) {
        newErrors.longitude = 'Must be between -180 and 180';
      }
    }
    
    // Optional numeric fields
    if (form.altitude.trim()) {
      const alt = parseFloat(form.altitude);
      if (isNaN(alt)) {
        newErrors.altitude = 'Must be a number';
      }
    }
    
    if (form.accuracy.trim()) {
      const acc = parseFloat(form.accuracy);
      if (isNaN(acc) || acc < 0) {
        newErrors.accuracy = 'Must be non-negative';
      }
    }
    
    if (form.speed.trim()) {
      const spd = parseFloat(form.speed);
      if (isNaN(spd) || spd < 0) {
        newErrors.speed = 'Must be non-negative';
      }
    }
    
    if (form.bearing.trim()) {
      const brg = parseFloat(form.bearing);
      if (isNaN(brg) || brg < 0 || brg > 360) {
        newErrors.bearing = 'Must be between 0 and 360';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [form]);

  // Submit the form
  const handleSubmit = useCallback(async () => {
    if (!validate()) return;
    
    setIsSubmitting(true);
    try {
      const request: UpdateLocationRequest = {
        latitude: parseFloat(form.latitude),
        longitude: parseFloat(form.longitude),
      };
      
      if (form.address.trim()) request.address = form.address.trim();
      if (form.namedLocation.trim()) request.named_location = form.namedLocation.trim();
      if (form.altitude.trim()) request.altitude = parseFloat(form.altitude);
      if (form.accuracy.trim()) request.accuracy = parseFloat(form.accuracy);
      if (form.speed.trim()) request.speed = parseFloat(form.speed);
      if (form.bearing.trim()) request.bearing = parseFloat(form.bearing);
      
      await onSubmit(request);
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to update location:', error);
      toast.error('Failed to update location');
    } finally {
      setIsSubmitting(false);
    }
  }, [form, validate, onSubmit, onOpenChange]);

  // Save current form as a named location
  const handleSaveLocation = useCallback(() => {
    if (!saveName.trim()) {
      toast.error('Please enter a name');
      return;
    }
    
    const lat = parseFloat(form.latitude);
    const lng = parseFloat(form.longitude);
    
    if (isNaN(lat) || isNaN(lng)) {
      toast.error('Please enter valid coordinates first');
      return;
    }
    
    onSaveLocation(
      saveName.trim(),
      lat,
      lng,
      form.address.trim() || undefined,
      form.altitude.trim() ? parseFloat(form.altitude) : undefined
    );
    
    toast.success(`Saved "${saveName.trim()}" to quick select`);
    setShowSaveDialog(false);
    setSaveName('');
  }, [saveName, form, onSaveLocation]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            Update Location
          </DialogTitle>
          <DialogDescription>
            Set the simulated user location with coordinates and optional metadata.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Quick Select - Saved Locations */}
          {savedLocations.length > 0 && (
            <div className="space-y-2">
              <Label className="text-sm font-medium">Quick Select</Label>
              <div className="flex flex-wrap gap-2">
                {savedLocations.map((saved) => (
                  <div key={saved.id} className="flex items-center gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8"
                      onClick={() => applySavedLocation(saved)}
                    >
                      <MapPin className="h-3 w-3 mr-1" />
                      {saved.name}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                      onClick={() => {
                        onDeleteSavedLocation(saved.id);
                        toast.success(`Removed "${saved.name}"`);
                      }}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Contact Addresses */}
          {contactAddresses.length > 0 && (
            <div className="space-y-2">
              <Label className="text-sm font-medium">Contact Addresses</Label>
              <div className="flex flex-wrap gap-2">
                {contactAddresses.map((entry) => (
                  <Button
                    key={`${entry.contact_id}-${entry.address_oneline}`}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8"
                    onClick={() => {
                      setForm(prev => ({
                        ...prev,
                        address: entry.address_oneline,
                        namedLocation: `${entry.display_name}${entry.label ? ` (${entry.label})` : ''}`,
                        ...(entry.latitude != null && entry.longitude != null
                          ? { latitude: String(entry.latitude), longitude: String(entry.longitude) }
                          : {}),
                      }));
                      toast.info(`Selected ${entry.display_name}'s address`);
                    }}
                  >
                    <Navigation className="h-3 w-3 mr-1" />
                    {entry.display_name}{entry.label ? ` (${entry.label})` : ''}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {/* Save current as... */}
          <div className="flex items-center gap-2">
            {!showSaveDialog ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowSaveDialog(true)}
                disabled={!form.latitude || !form.longitude}
              >
                <Plus className="h-4 w-4 mr-1" />
                Save Current as...
              </Button>
            ) : (
              <div className="flex items-center gap-2 flex-1">
                <Input
                  placeholder="Location name (e.g., Home, Office)"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSaveLocation()}
                  className="h-8"
                />
                <Button
                  type="button"
                  size="sm"
                  className="h-8"
                  onClick={handleSaveLocation}
                >
                  <Save className="h-4 w-4 mr-1" />
                  Save
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8"
                  onClick={() => {
                    setShowSaveDialog(false);
                    setSaveName('');
                  }}
                >
                  Cancel
                </Button>
              </div>
            )}
          </div>

          <Separator />

          {/* Address Search Section */}
          <div className="space-y-3">
            <Label className="text-sm font-medium flex items-center gap-2">
              <Search className="h-4 w-4" />
              Search by Address
            </Label>
            
            <div className="relative">
              <Input
                ref={searchInputRef}
                type="text"
                placeholder="Type an address to search..."
                value={addressSearch}
                onChange={(e) => setAddressSearch(e.target.value)}
                className="pr-8"
              />
              {isSearching && (
                <Loader2 className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
              )}
            </div>
            
            {/* Search Results Dropdown */}
            {showSearchResults && searchResults.length > 0 && (
              <div className="border rounded-md bg-background shadow-lg max-h-48 overflow-auto">
                {searchResults.map((result, index) => (
                  <button
                    key={index}
                    type="button"
                    className="w-full text-left px-3 py-2 text-sm hover:bg-muted border-b last:border-b-0 transition-colors"
                    onClick={() => applySearchResult(result)}
                  >
                    <p className="font-medium truncate">{result.displayName.split(',')[0]}</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {result.displayName.split(',').slice(1).join(',').trim()}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>

          <Separator />

          {/* Coordinates Section */}
          <div className="space-y-4">
            <Label className="text-sm font-medium flex items-center gap-2">
              <Navigation className="h-4 w-4" />
              Coordinates
            </Label>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="latitude" className="text-xs">
                  Latitude <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="latitude"
                  type="number"
                  step="any"
                  min="-90"
                  max="90"
                  placeholder="e.g., 37.7749"
                  value={form.latitude}
                  onChange={(e) => updateField('latitude', e.target.value)}
                  className={errors.latitude ? 'border-destructive' : ''}
                />
                {errors.latitude && (
                  <p className="text-xs text-destructive">{errors.latitude}</p>
                )}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="longitude" className="text-xs">
                  Longitude <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="longitude"
                  type="number"
                  step="any"
                  min="-180"
                  max="180"
                  placeholder="e.g., -122.4194"
                  value={form.longitude}
                  onChange={(e) => updateField('longitude', e.target.value)}
                  className={errors.longitude ? 'border-destructive' : ''}
                />
                {errors.longitude && (
                  <p className="text-xs text-destructive">{errors.longitude}</p>
                )}
              </div>
            </div>

            {/* Map Picker */}
            {showMapPicker ? (
              <MapPicker
                initialLat={form.latitude ? parseFloat(form.latitude) : undefined}
                initialLng={form.longitude ? parseFloat(form.longitude) : undefined}
                onConfirm={applyMapSelection}
                onCancel={() => setShowMapPicker(false)}
              />
            ) : (
              /* Preset Cities and Pick on Map */
              <div className="flex items-center gap-2 flex-wrap">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8"
                  onClick={() => setShowMapPicker(true)}
                >
                  <Map className="h-4 w-4 mr-1" />
                  Pick on Map
                </Button>
                <span className="text-xs text-muted-foreground">or</span>
                <Select onValueChange={applyPresetCity}>
                  <SelectTrigger className="w-48 h-8">
                    <SelectValue placeholder="Select a preset city" />
                  </SelectTrigger>
                  <SelectContent>
                    <ScrollArea className="h-48">
                      {PRESET_CITIES.map((city) => (
                        <SelectItem key={city.name} value={city.name}>
                          {city.name}, {city.country}
                        </SelectItem>
                      ))}
                    </ScrollArea>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>

          <Separator />

          {/* Location Info Section */}
          <div className="space-y-4">
            <Label className="text-sm font-medium">Location Info (Optional)</Label>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="namedLocation" className="text-xs">
                  Named Location
                </Label>
                <Input
                  id="namedLocation"
                  placeholder="e.g., Home, Office, Gym"
                  value={form.namedLocation}
                  onChange={(e) => updateField('namedLocation', e.target.value)}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="address" className="text-xs">
                  Address
                </Label>
                <Input
                  id="address"
                  placeholder="Human-readable address"
                  value={form.address}
                  onChange={(e) => updateField('address', e.target.value)}
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* Motion Data Section */}
          <div className="space-y-4">
            <Label className="text-sm font-medium">Motion Data (Optional)</Label>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="altitude" className="text-xs">
                  Altitude (meters)
                </Label>
                <Input
                  id="altitude"
                  type="number"
                  step="any"
                  placeholder="e.g., 52"
                  value={form.altitude}
                  onChange={(e) => updateField('altitude', e.target.value)}
                  className={errors.altitude ? 'border-destructive' : ''}
                />
                {errors.altitude && (
                  <p className="text-xs text-destructive">{errors.altitude}</p>
                )}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="accuracy" className="text-xs">
                  Accuracy (meters)
                </Label>
                <Input
                  id="accuracy"
                  type="number"
                  step="any"
                  min="0"
                  placeholder="e.g., 15"
                  value={form.accuracy}
                  onChange={(e) => updateField('accuracy', e.target.value)}
                  className={errors.accuracy ? 'border-destructive' : ''}
                />
                {errors.accuracy && (
                  <p className="text-xs text-destructive">{errors.accuracy}</p>
                )}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="speed" className="text-xs">
                  Speed (m/s)
                </Label>
                <Input
                  id="speed"
                  type="number"
                  step="any"
                  min="0"
                  placeholder="e.g., 0"
                  value={form.speed}
                  onChange={(e) => updateField('speed', e.target.value)}
                  className={errors.speed ? 'border-destructive' : ''}
                />
                {errors.speed && (
                  <p className="text-xs text-destructive">{errors.speed}</p>
                )}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="bearing" className="text-xs">
                  Bearing (0-360°)
                </Label>
                <Input
                  id="bearing"
                  type="number"
                  step="any"
                  min="0"
                  max="360"
                  placeholder="0=N, 90=E, 180=S, 270=W"
                  value={form.bearing}
                  onChange={(e) => updateField('bearing', e.target.value)}
                  className={errors.bearing ? 'border-destructive' : ''}
                />
                {errors.bearing && (
                  <p className="text-xs text-destructive">{errors.bearing}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Updating...' : 'Update Location'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
