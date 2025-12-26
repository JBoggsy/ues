/**
 * Main application header with simulation status and global controls.
 */
import { useState, useEffect, useCallback } from 'react';
import { 
  Play, 
  Pause, 
  Square, 
  RotateCcw, 
  Undo, 
  Redo,
  Download,
  Upload,
  FolderOpen,
  Menu
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { 
  useSimulationStatus, 
  useStartSimulation, 
  useStopSimulation,
  useUndo,
  useRedo 
} from '@/api';
import { usePauseTime, useResumeTime } from '@/api';
import { TimeDisplay } from '@/components/simulation/TimeDisplay';
import { ExportDialog, ImportDialog } from '@/components/scenario';

export function Header() {
  const { data: status } = useSimulationStatus();
  const startSimulation = useStartSimulation();
  const stopSimulation = useStopSimulation();
  const pauseTime = usePauseTime();
  const resumeTime = useResumeTime();
  const undo = useUndo();
  const redo = useRedo();

  // Dialog state
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);

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

  // Keyboard shortcuts
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Ignore if user is typing in an input field
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
      return;
    }

    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const modKey = isMac ? e.metaKey : e.ctrlKey;

    if (modKey && e.key === 's') {
      e.preventDefault();
      setShowExportDialog(true);
    } else if (modKey && e.key === 'o') {
      e.preventDefault();
      setShowImportDialog(true);
    }
  }, []);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <>
      <header className="border-b bg-background px-4 py-2">
        <div className="flex items-center justify-between">
          {/* Left: Menu, Title and Status */}
          <div className="flex items-center gap-4">
            {/* Scenario Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon">
                  <Menu className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem onClick={() => setShowExportDialog(true)}>
                  <Download className="h-4 w-4 mr-2" />
                  Export Scenario...
                  <span className="ml-auto text-xs text-muted-foreground">⌘S</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setShowImportDialog(true)}>
                  <Upload className="h-4 w-4 mr-2" />
                  Import Scenario...
                  <span className="ml-auto text-xs text-muted-foreground">⌘O</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem disabled>
                  <FolderOpen className="h-4 w-4 mr-2" />
                  Open Recent
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

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

      {/* Scenario Dialogs */}
      <ExportDialog open={showExportDialog} onOpenChange={setShowExportDialog} />
      <ImportDialog open={showImportDialog} onOpenChange={setShowImportDialog} />
    </>
  );
}
