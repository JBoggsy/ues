/**
 * Displays the current simulation time.
 */
import { Clock } from 'lucide-react';
import { format } from 'date-fns';
import { useTimeState } from '@/api';
import { Badge } from '@/components/ui/badge';

export function TimeDisplay() {
  const { data: timeState, isLoading, isError } = useTimeState();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Clock className="h-4 w-4 animate-pulse" />
        <span className="font-mono text-sm">Loading...</span>
      </div>
    );
  }

  if (isError || !timeState) {
    return (
      <div className="flex items-center gap-2 text-destructive">
        <Clock className="h-4 w-4" />
        <span className="font-mono text-sm">Connection Error</span>
      </div>
    );
  }

  const currentTime = new Date(timeState.current_time);
  const formattedDate = format(currentTime, 'yyyy-MM-dd');
  const formattedTime = format(currentTime, 'HH:mm:ss');

  return (
    <div className="flex items-center gap-3">
      <Clock className="h-4 w-4 text-muted-foreground" />
      <div className="flex items-center gap-2">
        <span className="font-mono text-sm">{formattedDate}</span>
        <span className="font-mono text-lg font-semibold">{formattedTime}</span>
      </div>
      <Badge variant="outline" className="text-xs">
        {timeState.time_scale}x
      </Badge>
      {timeState.is_paused && (
        <Badge variant="secondary" className="text-xs">
          Paused
        </Badge>
      )}
    </div>
  );
}
