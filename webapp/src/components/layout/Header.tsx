/**
 * Main application header with simulation status and global controls.
 */
import { Play, Pause, Square, RotateCcw, Undo, Redo } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  useSimulationStatus, 
  useStartSimulation, 
  useStopSimulation,
  useUndo,
  useRedo 
} from '@/api';
import { usePauseTime, useResumeTime } from '@/api';
import { TimeDisplay } from '@/components/simulation/TimeDisplay';

export function Header() {
  const { data: status } = useSimulationStatus();
  const startSimulation = useStartSimulation();
  const stopSimulation = useStopSimulation();
  const pauseTime = usePauseTime();
  const resumeTime = useResumeTime();
  const undo = useUndo();
  const redo = useRedo();

  const isRunning = status?.is_running ?? false;
  const isPaused = status?.is_paused ?? false;

  const handlePlayPause = () => {
    if (!isRunning) {
      startSimulation.mutate({});
    } else if (isPaused) {
      resumeTime.mutate();
    } else {
      pauseTime.mutate();
    }
  };

  const handleStop = () => {
    stopSimulation.mutate();
  };

  return (
    <header className="border-b bg-background px-4 py-2">
      <div className="flex items-center justify-between">
        {/* Left: Title and Status */}
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold">UES Control Panel</h1>
          <Badge variant={isRunning ? (isPaused ? 'secondary' : 'default') : 'outline'}>
            {isRunning ? (isPaused ? 'Paused' : 'Running') : 'Stopped'}
          </Badge>
        </div>

        {/* Center: Time Display */}
        <div className="flex items-center gap-2">
          <TimeDisplay />
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-2">
          {/* Undo/Redo */}
          <Button
            variant="outline"
            size="icon"
            onClick={() => undo.mutate({})}
            title="Undo"
          >
            <Undo className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => redo.mutate({})}
            title="Redo"
          >
            <Redo className="h-4 w-4" />
          </Button>

          <Separator orientation="vertical" className="h-6" />

          {/* Simulation Controls */}
          <Button
            variant={isRunning && !isPaused ? 'secondary' : 'default'}
            size="icon"
            onClick={handlePlayPause}
            title={isRunning && !isPaused ? 'Pause' : 'Play'}
          >
            {isRunning && !isPaused ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4" />
            )}
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={handleStop}
            disabled={!isRunning}
            title="Stop"
          >
            <Square className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => window.confirm('Reset simulation?') && stopSimulation.mutate()}
            title="Reset"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
