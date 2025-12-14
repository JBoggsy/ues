/**
 * Time advancement controls (advance by duration, skip to next event).
 */
import { useState } from 'react';
import { FastForward, SkipForward } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAdvanceTime, useSkipToNext, useSimulationStatus } from '@/api';

export function TimeAdvanceControls() {
  const [minutes, setMinutes] = useState('5');
  const advanceTime = useAdvanceTime();
  const skipToNext = useSkipToNext();
  const { data: status } = useSimulationStatus();

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
    </div>
  );
}
