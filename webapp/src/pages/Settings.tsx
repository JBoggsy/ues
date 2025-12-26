/**
 * Settings page for configuring application preferences.
 */
import { Settings as SettingsIcon, RotateCcw, Sun, Moon, Monitor } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Separator } from '@/components/ui/separator';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { useSettingsStore, type Theme } from '@/lib/store';
import { toast } from 'sonner';

export function Settings() {
  const {
    apiUrl,
    connectionTimeout,
    timePollingInterval,
    environmentPollingInterval,
    eventsPollingInterval,
    theme,
    toastDuration,
    confirmDestructiveActions,
    displayTimezone,
    use24HourFormat,
    setApiUrl,
    setConnectionTimeout,
    setTimePollingInterval,
    setEnvironmentPollingInterval,
    setEventsPollingInterval,
    setTheme,
    setToastDuration,
    setConfirmDestructiveActions,
    setDisplayTimezone,
    setUse24HourFormat,
    resetToDefaults,
  } = useSettingsStore();

  const handleReset = () => {
    resetToDefaults();
    toast.success('Settings reset to defaults');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <SettingsIcon className="h-6 w-6" />
            Settings
          </h2>
          <p className="text-muted-foreground">
            Configure application preferences and connection settings
          </p>
        </div>
        <Button variant="outline" onClick={handleReset}>
          <RotateCcw className="h-4 w-4 mr-2" />
          Reset to Defaults
        </Button>
      </div>

      {/* Connection Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Connection</CardTitle>
          <CardDescription>
            Configure how the web UI connects to the simulation backend
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="apiUrl">API Base URL</Label>
            <Input
              id="apiUrl"
              type="url"
              placeholder="http://localhost:8000"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              The base URL of the UES simulation API server
            </p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="timeout">Connection Timeout (ms)</Label>
            <Input
              id="timeout"
              type="number"
              min={1000}
              max={60000}
              step={1000}
              value={connectionTimeout}
              onChange={(e) => setConnectionTimeout(Number(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">
              How long to wait for API responses before timing out (1000-60000ms)
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Polling Intervals */}
      <Card>
        <CardHeader>
          <CardTitle>Polling Intervals</CardTitle>
          <CardDescription>
            Configure how often the UI fetches data from the backend (lower = more responsive, higher = less load)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="timePolling">Time State Polling (ms)</Label>
            <Input
              id="timePolling"
              type="number"
              min={100}
              max={10000}
              step={100}
              value={timePollingInterval}
              onChange={(e) => setTimePollingInterval(Number(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">
              How often to refresh the simulation time display (100-10000ms)
            </p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="envPolling">Environment State Polling (ms)</Label>
            <Input
              id="envPolling"
              type="number"
              min={1000}
              max={30000}
              step={1000}
              value={environmentPollingInterval}
              onChange={(e) => setEnvironmentPollingInterval(Number(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">
              How often to refresh modality states and summaries (1000-30000ms)
            </p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="eventsPolling">Events Polling (ms)</Label>
            <Input
              id="eventsPolling"
              type="number"
              min={1000}
              max={30000}
              step={1000}
              value={eventsPollingInterval}
              onChange={(e) => setEventsPollingInterval(Number(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">
              How often to refresh the event queue list (1000-30000ms)
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Display Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Display</CardTitle>
          <CardDescription>
            Customize the appearance and behavior of the UI
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label>Theme</Label>
            <ToggleGroup
              type="single"
              value={theme}
              onValueChange={(value) => value && setTheme(value as Theme)}
              className="justify-start"
            >
              <ToggleGroupItem value="light" aria-label="Light mode">
                <Sun className="h-4 w-4 mr-2" />
                Light
              </ToggleGroupItem>
              <ToggleGroupItem value="dark" aria-label="Dark mode">
                <Moon className="h-4 w-4 mr-2" />
                Dark
              </ToggleGroupItem>
              <ToggleGroupItem value="system" aria-label="System preference">
                <Monitor className="h-4 w-4 mr-2" />
                System
              </ToggleGroupItem>
            </ToggleGroup>
          </div>

          <Separator />

          <div className="grid gap-2">
            <Label htmlFor="toastDuration">Toast Notification Duration (ms)</Label>
            <Input
              id="toastDuration"
              type="number"
              min={1000}
              max={10000}
              step={500}
              value={toastDuration}
              onChange={(e) => setToastDuration(Number(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">
              How long success/error messages stay visible (1000-10000ms)
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="confirmDestructive"
              checked={confirmDestructiveActions}
              onCheckedChange={(checked) => 
                setConfirmDestructiveActions(checked === true)
              }
            />
            <div className="grid gap-1.5 leading-none">
              <Label htmlFor="confirmDestructive" className="cursor-pointer">
                Confirm destructive actions
              </Label>
              <p className="text-xs text-muted-foreground">
                Show confirmation dialog before reset, clear, or bulk delete operations
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Time Display Settings (Placeholders) */}
      <Card>
        <CardHeader>
          <CardTitle>Time Display</CardTitle>
          <CardDescription>
            Configure how times are displayed throughout the UI
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="displayTimezone">Display Timezone</Label>
            <Select
              value={displayTimezone}
              onValueChange={(value) => setDisplayTimezone(value as 'simulator' | 'browser')}
            >
              <SelectTrigger id="displayTimezone">
                <SelectValue placeholder="Select timezone mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="simulator">Simulator Timezone</SelectItem>
                <SelectItem value="browser">Browser Local Time</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Whether to display times in the simulator's timezone or your local timezone
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="use24Hour"
              checked={use24HourFormat}
              onCheckedChange={(checked) => setUse24HourFormat(checked === true)}
            />
            <div className="grid gap-1.5 leading-none">
              <Label htmlFor="use24Hour" className="cursor-pointer">
                Use 24-hour format
              </Label>
              <p className="text-xs text-muted-foreground">
                Display times in 24-hour format instead of 12-hour AM/PM
              </p>
            </div>
          </div>

          <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
            Note: Time display settings are placeholders and not yet fully implemented throughout the UI.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
