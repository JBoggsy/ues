/**
 * Simulation status indicator with statistics.
 */
import { Activity, CheckCircle, Clock, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useSimulationStatus } from '@/api';

export function SimulationStatus() {
  const { data: status, isLoading, isError } = useSimulationStatus();

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Simulation Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  if (isError || !status) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Simulation Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-destructive">Failed to load status</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Activity className="h-4 w-4" />
          Simulation Status
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">Pending:</span>
            <span className="font-medium">{status.pending_events}</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-500" />
            <span className="text-muted-foreground">Executed:</span>
            <span className="font-medium">{status.executed_events}</span>
          </div>
          <div className="flex items-center gap-2">
            <XCircle className="h-4 w-4 text-red-500" />
            <span className="text-muted-foreground">Failed:</span>
            <span className="font-medium">{status.failed_events}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Mode:</span>
            <span className="font-medium capitalize">
              {status.is_paused ? 'Paused' : status.auto_advance ? 'Auto' : 'Manual'}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
