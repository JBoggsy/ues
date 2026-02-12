/**
 * Dialog for creating a new weather report for a location.
 * Supports presets and manual entry.
 */
import { useState, useCallback, useEffect, useMemo } from 'react';
import {
  Sun,
  Cloud,
  CloudRain,
  CloudLightning,
  CloudSun,
  Loader2,
  SlidersHorizontal,
  Sparkles,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type {
  WeatherReport,
  CurrentWeather,
  WeatherCondition,
  UnitSystem,
} from './types';
import {
  formatTemperature,
  formatWindSpeed,
  convertTemperature,
  convertWindSpeed,
  getWeatherEmoji,
  windDegToDirection,
} from './types';

interface NewWeatherReportDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog is closed */
  onOpenChange: (open: boolean) => void;
  /** Location latitude */
  latitude: number;
  /** Location longitude */
  longitude: number;
  /** Location display name */
  locationName: string;
  /** Current unit system (global preference) */
  units: UnitSystem;
  /** Callback when report is submitted */
  onSubmit: (report: WeatherReport) => Promise<void>;
}

// Weather condition presets with OpenWeather API codes
const SKY_CONDITIONS = [
  { id: 'sunny', label: 'Sunny', icon: Sun, conditionId: 800, main: 'Clear', description: 'clear sky', iconCode: '01d' },
  { id: 'partly', label: 'Partly Cloudy', icon: CloudSun, conditionId: 801, main: 'Clouds', description: 'few clouds', iconCode: '02d' },
  { id: 'cloudy', label: 'Cloudy', icon: Cloud, conditionId: 804, main: 'Clouds', description: 'overcast clouds', iconCode: '04d' },
  { id: 'rainy', label: 'Rainy', icon: CloudRain, conditionId: 500, main: 'Rain', description: 'light rain', iconCode: '10d' },
  { id: 'stormy', label: 'Stormy', icon: CloudLightning, conditionId: 211, main: 'Thunderstorm', description: 'thunderstorm', iconCode: '11d' },
] as const;

// Temperature presets in Kelvin (API standard)
const TEMP_PRESETS = [
  { id: 'hot', label: 'Hot', tempK: 308.15, emoji: '🔥' }, // 95°F / 35°C
  { id: 'warm', label: 'Warm', tempK: 297.04, emoji: '🌡️' }, // 75°F / 24°C
  { id: 'cool', label: 'Cool', tempK: 285.93, emoji: '🍃' }, // 55°F / 13°C
  { id: 'cold', label: 'Cold', tempK: 274.82, emoji: '❄️' }, // 35°F / 2°C
] as const;

// Wind presets in m/s (API standard)
const WIND_PRESETS = [
  { id: 'windy', label: 'Windy', speedMs: 8.94, emoji: '💨' }, // 20 mph
  { id: 'breezy', label: 'Breezy', speedMs: 4.47, emoji: '🌬️' }, // 10 mph
  { id: 'calm', label: 'Calm', speedMs: 0.89, emoji: '🍃' }, // 2 mph
] as const;

// Manual entry condition options
const CONDITION_OPTIONS = [
  { id: 800, main: 'Clear', description: 'clear sky', icon: '01d' },
  { id: 801, main: 'Clouds', description: 'few clouds', icon: '02d' },
  { id: 802, main: 'Clouds', description: 'scattered clouds', icon: '03d' },
  { id: 803, main: 'Clouds', description: 'broken clouds', icon: '04d' },
  { id: 804, main: 'Clouds', description: 'overcast clouds', icon: '04d' },
  { id: 500, main: 'Rain', description: 'light rain', icon: '10d' },
  { id: 501, main: 'Rain', description: 'moderate rain', icon: '10d' },
  { id: 502, main: 'Rain', description: 'heavy rain', icon: '10d' },
  { id: 211, main: 'Thunderstorm', description: 'thunderstorm', icon: '11d' },
  { id: 601, main: 'Snow', description: 'snow', icon: '13d' },
  { id: 701, main: 'Mist', description: 'mist', icon: '50d' },
  { id: 741, main: 'Fog', description: 'fog', icon: '50d' },
];

// Wind direction options
const WIND_DIRECTIONS = [
  { label: 'N', deg: 0 },
  { label: 'NE', deg: 45 },
  { label: 'E', deg: 90 },
  { label: 'SE', deg: 135 },
  { label: 'S', deg: 180 },
  { label: 'SW', deg: 225 },
  { label: 'W', deg: 270 },
  { label: 'NW', deg: 315 },
];

/**
 * Calculate related weather values based on preset selections.
 */
function calculateDerivedValues(
  skyId: string,
  tempK: number,
  windSpeedMs: number
): { humidity: number; clouds: number; pressure: number; visibility: number; uvi: number } {
  // Base values
  let humidity = 50;
  let clouds = 25;
  let pressure = 1013;
  let visibility = 10000;
  let uvi = 5;

  // Adjust based on sky condition
  switch (skyId) {
    case 'sunny':
      clouds = 5;
      humidity = 40;
      uvi = 7;
      break;
    case 'partly':
      clouds = 30;
      humidity = 50;
      uvi = 5;
      break;
    case 'cloudy':
      clouds = 90;
      humidity = 65;
      uvi = 2;
      break;
    case 'rainy':
      clouds = 80;
      humidity = 85;
      visibility = 5000;
      uvi = 1;
      pressure = 1005;
      break;
    case 'stormy':
      clouds = 95;
      humidity = 90;
      visibility = 2000;
      uvi = 0;
      pressure = 998;
      break;
  }

  // Adjust humidity based on temperature (hot = less humid unless rainy)
  if (tempK > 303) {
    // Hot
    if (skyId !== 'rainy' && skyId !== 'stormy') {
      humidity = Math.max(30, humidity - 15);
    }
  } else if (tempK < 280) {
    // Cold
    humidity = Math.min(80, humidity + 10);
  }

  // Adjust pressure based on wind (windy = lower pressure)
  if (windSpeedMs > 7) {
    pressure = Math.max(990, pressure - 10);
  }

  return { humidity, clouds, pressure, visibility, uvi };
}

/**
 * Convert user input temperature to Kelvin.
 */
function userTempToKelvin(temp: number, units: UnitSystem): number {
  switch (units) {
    case 'imperial':
      return (temp - 32) * 5 / 9 + 273.15;
    case 'metric':
      return temp + 273.15;
    case 'standard':
    default:
      return temp;
  }
}

/**
 * Convert Kelvin to user display temperature.
 */
function kelvinToUserTemp(kelvin: number, units: UnitSystem): number {
  return Math.round(convertTemperature(kelvin, units));
}

/**
 * Convert user input wind speed to m/s.
 */
function userWindToMs(speed: number, units: UnitSystem): number {
  if (units === 'imperial') {
    return speed / 2.23694; // mph to m/s
  }
  return speed; // metric and standard use m/s
}

/**
 * Convert m/s to user display wind speed.
 */
function msToUserWind(ms: number, units: UnitSystem): number {
  return Math.round(convertWindSpeed(ms, units));
}

export function NewWeatherReportDialog({
  open,
  onOpenChange,
  latitude,
  longitude,
  locationName,
  units,
  onSubmit,
}: NewWeatherReportDialogProps) {
  const [activeTab, setActiveTab] = useState<string>('presets');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Preset selections
  const [selectedSky, setSelectedSky] = useState<string>('sunny');
  const [selectedTemp, setSelectedTemp] = useState<string>('warm');
  const [selectedWind, setSelectedWind] = useState<string>('breezy');

  // Manual entry state (stored in user's unit preference)
  const [manualCondition, setManualCondition] = useState<string>('800');
  const [manualTemp, setManualTemp] = useState<string>('72');
  const [manualFeelsLike, setManualFeelsLike] = useState<string>('72');
  const [manualHumidity, setManualHumidity] = useState<string>('50');
  const [manualPressure, setManualPressure] = useState<string>('1013');
  const [manualWindSpeed, setManualWindSpeed] = useState<string>('10');
  const [manualWindDir, setManualWindDir] = useState<string>('180');
  const [manualClouds, setManualClouds] = useState<string>('25');
  const [manualVisibility, setManualVisibility] = useState<string>('10');
  const [manualUvi, setManualUvi] = useState<string>('5');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setActiveTab('presets');
      setSelectedSky('sunny');
      setSelectedTemp('warm');
      setSelectedWind('breezy');
      // Set manual defaults based on units
      const defaultTempK = 295.37; // ~72°F
      setManualTemp(kelvinToUserTemp(defaultTempK, units).toString());
      setManualFeelsLike(kelvinToUserTemp(defaultTempK, units).toString());
      setManualWindSpeed(msToUserWind(4.47, units).toString());
    }
  }, [open, units]);

  // Build preview report based on current selections
  const previewReport = useMemo((): WeatherReport | null => {
    const now = Math.floor(Date.now() / 1000);
    const sixHours = 6 * 60 * 60;

    if (activeTab === 'presets') {
      const sky = SKY_CONDITIONS.find((s) => s.id === selectedSky);
      const temp = TEMP_PRESETS.find((t) => t.id === selectedTemp);
      const wind = WIND_PRESETS.find((w) => w.id === selectedWind);

      if (!sky || !temp || !wind) return null;

      const derived = calculateDerivedValues(selectedSky, temp.tempK, wind.speedMs);

      const condition: WeatherCondition = {
        id: sky.conditionId,
        main: sky.main,
        description: sky.description,
        icon: sky.iconCode,
      };

      const current: CurrentWeather = {
        dt: now,
        sunrise: now - sixHours,
        sunset: now + sixHours,
        temp: temp.tempK,
        feels_like: temp.tempK,
        pressure: derived.pressure,
        humidity: derived.humidity,
        dew_point: temp.tempK - 10,
        uvi: derived.uvi,
        clouds: derived.clouds,
        visibility: derived.visibility,
        wind_speed: wind.speedMs,
        wind_deg: 180,
        weather: [condition],
      };

      return {
        lat: latitude,
        lon: longitude,
        timezone: 'UTC',
        timezone_offset: 0,
        current,
      };
    }

    if (activeTab === 'manual') {
      const conditionOpt = CONDITION_OPTIONS.find((c) => c.id.toString() === manualCondition);
      if (!conditionOpt) return null;

      const tempK = userTempToKelvin(parseFloat(manualTemp) || 295, units);
      const feelsLikeK = userTempToKelvin(parseFloat(manualFeelsLike) || 295, units);
      const windMs = userWindToMs(parseFloat(manualWindSpeed) || 0, units);

      const condition: WeatherCondition = {
        id: conditionOpt.id,
        main: conditionOpt.main,
        description: conditionOpt.description,
        icon: conditionOpt.icon,
      };

      const current: CurrentWeather = {
        dt: now,
        sunrise: now - sixHours,
        sunset: now + sixHours,
        temp: tempK,
        feels_like: feelsLikeK,
        pressure: parseInt(manualPressure) || 1013,
        humidity: parseInt(manualHumidity) || 50,
        dew_point: tempK - 10,
        uvi: parseFloat(manualUvi) || 5,
        clouds: parseInt(manualClouds) || 25,
        visibility: (parseFloat(manualVisibility) || 10) * 1000,
        wind_speed: windMs,
        wind_deg: parseInt(manualWindDir) || 180,
        weather: [condition],
      };

      return {
        lat: latitude,
        lon: longitude,
        timezone: 'UTC',
        timezone_offset: 0,
        current,
      };
    }

    return null;
  }, [
    activeTab,
    selectedSky,
    selectedTemp,
    selectedWind,
    manualCondition,
    manualTemp,
    manualFeelsLike,
    manualHumidity,
    manualPressure,
    manualWindSpeed,
    manualWindDir,
    manualClouds,
    manualVisibility,
    manualUvi,
    latitude,
    longitude,
    units,
  ]);

  // Submit the weather report
  const handleSubmit = useCallback(async () => {
    if (!previewReport) {
      toast.error('No weather data to submit');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(previewReport);
      toast.success('Weather report added');
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to submit weather report:', error);
      toast.error('Failed to add weather report');
    } finally {
      setIsSubmitting(false);
    }
  }, [previewReport, onSubmit, onOpenChange]);

  // Unit labels
  const tempUnit = units === 'imperial' ? '°F' : units === 'metric' ? '°C' : 'K';
  const windUnit = units === 'imperial' ? 'mph' : 'm/s';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            New Weather Report
          </DialogTitle>
          <DialogDescription>
            Add weather data for: {locationName} ({latitude.toFixed(2)}, {longitude.toFixed(2)})
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="presets" className="gap-1">
              <Sparkles className="h-3 w-3" />
              Presets
            </TabsTrigger>
            <TabsTrigger value="manual" className="gap-1">
              <SlidersHorizontal className="h-3 w-3" />
              Manual
            </TabsTrigger>
          </TabsList>

          {/* Presets Tab */}
          <TabsContent value="presets" className="flex-1 space-y-4 mt-4 overflow-y-auto">
            {/* Sky Condition */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Sky Condition</Label>
              <div className="grid grid-cols-5 gap-2">
                {SKY_CONDITIONS.map((sky) => {
                  const Icon = sky.icon;
                  const isSelected = selectedSky === sky.id;
                  return (
                    <Card
                      key={sky.id}
                      className={cn(
                        'cursor-pointer transition-colors hover:bg-accent/50',
                        isSelected && 'border-primary bg-accent'
                      )}
                      onClick={() => setSelectedSky(sky.id)}
                    >
                      <CardContent className="p-2 text-center">
                        <Icon className="h-6 w-6 mx-auto mb-1" />
                        <p className="text-xs font-medium">{sky.label}</p>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>

            {/* Temperature */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Temperature</Label>
              <div className="grid grid-cols-4 gap-2">
                {TEMP_PRESETS.map((temp) => {
                  const isSelected = selectedTemp === temp.id;
                  const displayTemp = kelvinToUserTemp(temp.tempK, units);
                  return (
                    <Card
                      key={temp.id}
                      className={cn(
                        'cursor-pointer transition-colors hover:bg-accent/50',
                        isSelected && 'border-primary bg-accent'
                      )}
                      onClick={() => setSelectedTemp(temp.id)}
                    >
                      <CardContent className="p-2 text-center">
                        <span className="text-xl">{temp.emoji}</span>
                        <p className="text-xs font-medium">{temp.label}</p>
                        <p className="text-xs text-muted-foreground">
                          {displayTemp}{tempUnit}
                        </p>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>

            {/* Wind */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Wind</Label>
              <div className="grid grid-cols-3 gap-2">
                {WIND_PRESETS.map((wind) => {
                  const isSelected = selectedWind === wind.id;
                  const displaySpeed = msToUserWind(wind.speedMs, units);
                  return (
                    <Card
                      key={wind.id}
                      className={cn(
                        'cursor-pointer transition-colors hover:bg-accent/50',
                        isSelected && 'border-primary bg-accent'
                      )}
                      onClick={() => setSelectedWind(wind.id)}
                    >
                      <CardContent className="p-2 text-center">
                        <span className="text-xl">{wind.emoji}</span>
                        <p className="text-xs font-medium">{wind.label}</p>
                        <p className="text-xs text-muted-foreground">
                          {displaySpeed} {windUnit}
                        </p>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          </TabsContent>

          {/* Manual Entry Tab */}
          <TabsContent value="manual" className="flex-1 space-y-4 mt-4 overflow-y-auto">
            {/* Condition */}
            <div className="space-y-2">
              <Label>Condition</Label>
              <Select value={manualCondition} onValueChange={setManualCondition}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CONDITION_OPTIONS.map((opt) => (
                    <SelectItem key={opt.id} value={opt.id.toString()}>
                      {getWeatherEmoji(opt.icon)} {opt.description}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Temperature and Feels Like */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Temperature ({tempUnit})</Label>
                <Input
                  type="number"
                  value={manualTemp}
                  onChange={(e) => setManualTemp(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Feels Like ({tempUnit})</Label>
                <Input
                  type="number"
                  value={manualFeelsLike}
                  onChange={(e) => setManualFeelsLike(e.target.value)}
                />
              </div>
            </div>

            {/* Humidity and Pressure */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Humidity (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={manualHumidity}
                  onChange={(e) => setManualHumidity(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Pressure (hPa)</Label>
                <Input
                  type="number"
                  value={manualPressure}
                  onChange={(e) => setManualPressure(e.target.value)}
                />
              </div>
            </div>

            {/* Wind Speed and Direction */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Wind Speed ({windUnit})</Label>
                <Input
                  type="number"
                  min="0"
                  value={manualWindSpeed}
                  onChange={(e) => setManualWindSpeed(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Wind Direction</Label>
                <Select value={manualWindDir} onValueChange={setManualWindDir}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WIND_DIRECTIONS.map((dir) => (
                      <SelectItem key={dir.deg} value={dir.deg.toString()}>
                        {dir.label} ({dir.deg}°)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Advanced Options */}
            <div className="space-y-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="p-0 h-auto"
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                {showAdvanced ? (
                  <ChevronDown className="h-4 w-4 mr-1" />
                ) : (
                  <ChevronRight className="h-4 w-4 mr-1" />
                )}
                Advanced Options
              </Button>

              {showAdvanced && (
                <div className="grid grid-cols-3 gap-4 p-3 border rounded-lg bg-muted/50">
                  <div className="space-y-2">
                    <Label className="text-xs">Cloud Cover (%)</Label>
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      value={manualClouds}
                      onChange={(e) => setManualClouds(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs">UV Index</Label>
                    <Input
                      type="number"
                      min="0"
                      max="12"
                      step="0.1"
                      value={manualUvi}
                      onChange={(e) => setManualUvi(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs">Visibility (km)</Label>
                    <Input
                      type="number"
                      min="0"
                      value={manualVisibility}
                      onChange={(e) => setManualVisibility(e.target.value)}
                    />
                  </div>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>

        {/* Preview Section */}
        {previewReport?.current && (
          <div className="border rounded-lg p-3 bg-muted/30 mt-4">
            <h4 className="text-xs font-medium text-muted-foreground mb-2">PREVIEW</h4>
            <div className="flex items-center gap-3">
              <span className="text-2xl">
                {previewReport.current.weather?.[0]
                  ? getWeatherEmoji(previewReport.current.weather[0].icon)
                  : '🌡️'}
              </span>
              <div className="flex-1">
                <p className="text-sm">
                  <span className="font-medium capitalize">
                    {previewReport.current.weather?.[0]?.description || 'Unknown'}
                  </span>
                  {' • '}
                  <span className="font-semibold">
                    {formatTemperature(previewReport.current.temp, units)}
                  </span>
                  {' • '}
                  <span>
                    {formatWindSpeed(previewReport.current.wind_speed, units)}{' '}
                    {windDegToDirection(previewReport.current.wind_deg)}
                  </span>
                </p>
                <p className="text-xs text-muted-foreground">
                  Humidity: {previewReport.current.humidity}%
                  {' • '}
                  Pressure: {previewReport.current.pressure} hPa
                  {' • '}
                  Clouds: {previewReport.current.clouds}%
                </p>
              </div>
            </div>
          </div>
        )}

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !previewReport}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Adding...
              </>
            ) : (
              'Add Weather Report'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
