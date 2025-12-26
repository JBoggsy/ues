/**
 * Time advancement controls (advance by duration, skip to next event, set time).
 */
import { useState, useEffect } from 'react';
import { FastForward, SkipForward, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAdvanceTime, useSkipToNext, useSetTime, useSimulationStatus, useTimeState } from '@/api';

export function TimeAdvanceControls() {
  const [minutes, setMinutes] = useState('5');
  const [targetTime, setTargetTime] = useState('');
  const advanceTime = useAdvanceTime();
  const skipToNext = useSkipToNext();
  const setTime = useSetTime();
  const { data: status } = useSimulationStatus();
  const { data: timeState } = useTimeState();

  // Simulation must be running (started and not paused) to advance time
  const isSimulationRunning = status?.is_running && !status?.is_paused;

  const handleAdvance = () => {
    const mins = parseInt(minutes, 10);
    if (!isNaN(mins) && mins > 0) {
      // Convert minutes to seconds as the API expects seconds
      advanceTime.mutate({ seconds: mins * 60 });
    }
  };

  const handleSkipToNext = () => {
    skipToNext.mutate();
  };

  const handleSetTime = () => {
    if (!targetTime) {
      toast.warning('No time selected', {
        description: 'Please select a target time.',
      });
      return;
    }
    // Convert local datetime to ISO string with timezone
    const targetDate = new Date(targetTime);
    setTime.mutate(
      { target_time: targetDate.toISOString() },
      {
        onSuccess: (data) => {
          const rolledBack = (data as unknown as { rolled_back_events?: number }).rolled_back_events || 0;
          const resetSkipped = (data as unknown as { reset_skipped_events?: number }).reset_skipped_events || 0;
          
          if (rolledBack > 0 || resetSkipped > 0) {
            toast.success('Time set (backwards)', {
              description: `Rolled back ${rolledBack} events, reset ${resetSkipped} skipped events`,
            });
          } else {
            toast.success('Time set', {
              description: `Executed ${data.executed_events} events`,
            });
          }
        },
        onError: (error) => {
          toast.error('Failed to set time', {
            description: error.message,
          });
        },
      }
    );
  };

  // Initialize targetTime from current simulator time when available
  useEffect(() => {
    if (timeState?.current_time && !targetTime) {
      // Convert to local datetime format for datetime-local input
      const date = new Date(timeState.current_time);
      const localDatetime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16);
      setTargetTime(localDatetime);
    }
  }, [timeState?.current_time]); // Only run when simulator time loads initially

  const showDisabledToast = () => {
    if (!status?.is_running) {
      toast.warning('Simulation not started', {
        description: 'Start the simulation first to advance time.',
      });
    } else if (status?.is_paused) {
      toast.warning('Simulation paused', {
        description: 'Resume the simulation to advance time.',
      });
    }
  };

  return (
    <div className="space-y-3">
      <span className="text-sm font-medium">Time Advance</span>
      
      <div className="flex gap-2">
        <Input
          type="number"
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
          placeholder="Minutes"
          min="1"
          className="w-24"
        />
        <div onClick={!isSimulationRunning ? showDisabledToast : undefined}>
          <Button
            variant="outline"
            onClick={handleAdvance}
            disabled={advanceTime.isPending || !isSimulationRunning}
          >
            <FastForward className="mr-2 h-4 w-4" />
            Advance
          </Button>
        </div>
      </div>

      <div onClick={!isSimulationRunning ? showDisabledToast : undefined}>
        <Button
          variant="outline"
          onClick={handleSkipToNext}
          disabled={skipToNext.isPending || !isSimulationRunning}
          className="w-full"
        >
          <SkipForward className="mr-2 h-4 w-4" />
          Skip to Next Event
        </Button>
      </div>

      {/* Set Time Section */}
      <div className="border-t pt-3 mt-3">
        <span className="text-sm font-medium">Set Time</span>
        <div className="flex gap-2 mt-2">
          <Input
            type="datetime-local"
            value={targetTime}
            onChange={(e) => setTargetTime(e.target.value)}
            className="flex-1"
          />
          <div onClick={!isSimulationRunning ? showDisabledToast : undefined}>
            <Button
              variant="outline"
              onClick={handleSetTime}
              disabled={setTime.isPending || !isSimulationRunning}
            >
              <Clock className="mr-2 h-4 w-4" />
              Set
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
