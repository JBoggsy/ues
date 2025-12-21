/**
 * Status bar component for weather viewer.
 * Shows last sync time, unit toggle, and location count.
 */
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { UnitSystem } from './types';

interface WeatherStatusBarProps {
  /** Last updated timestamp (ISO string) */
  lastUpdated?: string;
  /** Number of tracked locations */
  locationCount: number;
  /** Current unit system */
  units: UnitSystem;
  /** Callback when units change */
  onUnitsChange: (units: UnitSystem) => void;
}

/**
 * Format ISO timestamp to readable date/time.
 */
function formatLastSynced(isoString?: string): string {
  if (!isoString) return 'Never';
  const date = new Date(isoString);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function WeatherStatusBar({
  lastUpdated,
  locationCount,
  units,
  onUnitsChange,
}: WeatherStatusBarProps) {
  return (
    <div className="flex items-center justify-between px-4 py-2 bg-muted/50 border-t text-sm">
      <div className="text-muted-foreground">
        Last synced: {formatLastSynced(lastUpdated)}
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Units:</span>
          <Select value={units} onValueChange={(v) => onUnitsChange(v as UnitSystem)}>
            <SelectTrigger className="w-32 h-7 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="imperial">Imperial (°F)</SelectItem>
              <SelectItem value="metric">Metric (°C)</SelectItem>
              <SelectItem value="standard">Standard (K)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        <div className="text-muted-foreground">
          {locationCount} location{locationCount !== 1 ? 's' : ''}
        </div>
      </div>
    </div>
  );
}
