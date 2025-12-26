/**
 * Import Dialog component for loading simulation state from files.
 * 
 * Allows users to import:
 * - Environment files (.ues-env.json)
 * - Event queue files (.ues-events.json)
 * - Full scenario files (.ues-scenario.json)
 * 
 * Auto-detects file type and provides appropriate options.
 */
import { useState, useCallback, useRef } from 'react';
import { Upload, FileJson, AlertCircle, CheckCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  useImportEnvironment,
  useImportEvents,
  useImportScenario,
  readJsonFile,
  detectFileType,
} from '@/api';
import type {
  ExportedEnvironmentData,
  ExportedEventQueueData,
  ExportedScenarioData,
  HistoricEventHandling,
  ScenarioMetadata,
} from '@/api/types/scenario';
import { CompatibilityDialog } from './CompatibilityDialog';
import { useSimulationStatus } from '@/api';

interface ImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type DetectedFileType = 'environment' | 'events' | 'scenario' | null;

interface ParsedFile {
  type: DetectedFileType;
  data: unknown;
  filename: string;
  metadata?: ScenarioMetadata;
}

export function ImportDialog({ open, onOpenChange }: ImportDialogProps) {
  const [parsedFile, setParsedFile] = useState<ParsedFile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Options state
  const [historicEventHandling, setHistoricEventHandling] = useState<HistoricEventHandling>('ignore');
  const [strictModalities, setStrictModalities] = useState(false);
  const [mergeEvents, setMergeEvents] = useState(false);

  // Compatibility dialog state
  const [showCompatibilityDialog, setShowCompatibilityDialog] = useState(false);
  const [compatibilityWarnings, setCompatibilityWarnings] = useState<string[]>([]);

  const { data: simulationStatus } = useSimulationStatus();
  const importEnvironment = useImportEnvironment();
  const importEvents = useImportEvents();
  const importScenario = useImportScenario();

  const isSimulationRunning = simulationStatus?.is_running ?? false;

  const resetState = useCallback(() => {
    setParsedFile(null);
    setHistoricEventHandling('ignore');
    setStrictModalities(false);
    setMergeEvents(false);
    setCompatibilityWarnings([]);
  }, []);

  const handleFileSelect = useCallback(async (file: File) => {
    setIsLoading(true);
    try {
      const data = await readJsonFile(file);
      const type = detectFileType(data);
      
      if (!type) {
        toast.error('Unrecognized file format. Please select a valid UES scenario file.');
        return;
      }

      let metadata: ScenarioMetadata | undefined;
      if (type === 'scenario') {
        const scenario = data as ExportedScenarioData;
        metadata = scenario.metadata;
      }

      setParsedFile({
        type,
        data,
        filename: file.name,
        metadata,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to read file';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
    // Reset input so same file can be selected again
    e.target.value = '';
  }, [handleFileSelect]);

  const performImport = async () => {
    if (!parsedFile || !parsedFile.type) return;

    setIsImporting(true);
    try {
      switch (parsedFile.type) {
        case 'environment': {
          const result = await importEnvironment.mutateAsync({
            data: parsedFile.data as ExportedEnvironmentData,
            historicEventHandling,
            strictModalities,
          });
          
          if (result.warnings.length > 0 && !strictModalities) {
            toast.warning(`Loaded with warnings: ${result.warnings.join(', ')}`);
          } else {
            toast.success(`Loaded ${result.modalities_loaded.length} modalities`);
          }
          break;
        }
        case 'events': {
          const result = await importEvents.mutateAsync({
            data: parsedFile.data as ExportedEventQueueData,
            merge: mergeEvents,
          });
          
          const action = mergeEvents ? 'merged' : 'loaded';
          toast.success(`${result.events_loaded} events ${action}`);
          
          if (result.historic_events_warning) {
            toast.warning(`${result.historic_event_count} events are scheduled before current time`);
          }
          break;
        }
        case 'scenario': {
          const result = await importScenario.mutateAsync({
            scenario: parsedFile.data as ExportedScenarioData,
            strictModalities,
          });
          
          if (result.warnings.length > 0) {
            setCompatibilityWarnings(result.warnings);
            toast.warning('Scenario loaded with compatibility warnings');
          } else {
            toast.success(`Scenario loaded: ${result.modalities_loaded.length} modalities, ${result.events_loaded} events`);
          }
          break;
        }
      }
      
      onOpenChange(false);
      resetState();
    } catch (error) {
      // Check for specific error types
      if (error instanceof Error) {
        if (error.message.includes('409') || error.message.includes('running')) {
          toast.error('Cannot import while simulation is running. Please stop the simulation first.');
        } else if (error.message.includes('400') || error.message.includes('unknown modality')) {
          // Show compatibility dialog for strict mode errors
          setShowCompatibilityDialog(true);
          setCompatibilityWarnings([error.message]);
        } else {
          toast.error(error.message);
        }
      } else {
        toast.error('Import failed');
      }
    } finally {
      setIsImporting(false);
    }
  };

  const handleImport = () => {
    if (isSimulationRunning) {
      toast.error('Cannot import while simulation is running. Please stop the simulation first.');
      return;
    }
    performImport();
  };

  const handleClose = () => {
    resetState();
    onOpenChange(false);
  };

  const handleCompatibilityConfirm = () => {
    setShowCompatibilityDialog(false);
    setStrictModalities(false);
    performImport();
  };

  const fileTypeLabels: Record<NonNullable<DetectedFileType>, string> = {
    environment: 'Environment',
    events: 'Event Queue',
    scenario: 'Full Scenario',
  };

  return (
    <>
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="sm:max-w-[550px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Import Simulation State
            </DialogTitle>
            <DialogDescription>
              Load a previously saved simulation state from a JSON file.
            </DialogDescription>
          </DialogHeader>

          {isSimulationRunning && (
            <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-destructive">
              <AlertCircle className="h-4 w-4" />
              <span className="text-sm">
                Simulation is running. Stop it before importing.
              </span>
            </div>
          )}

          <div className="space-y-4 py-4">
            {/* File Drop Zone */}
            {!parsedFile ? (
              <div
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                  transition-colors
                  ${isDragging 
                    ? 'border-primary bg-primary/5' 
                    : 'border-muted-foreground/25 hover:border-primary/50'
                  }
                  ${isLoading ? 'opacity-50 pointer-events-none' : ''}
                `}
                onClick={() => fileInputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json,.ues-env.json,.ues-events.json,.ues-scenario.json"
                  className="hidden"
                  onChange={handleFileInputChange}
                />
                <FileJson className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  {isLoading ? (
                    'Reading file...'
                  ) : (
                    <>
                      Drag and drop a file here, or <span className="text-primary">browse</span>
                    </>
                  )}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Supports .ues-scenario.json, .ues-env.json, .ues-events.json
                </p>
              </div>
            ) : (
              /* File Preview */
              <div className="space-y-4">
                <div className="flex items-start justify-between rounded-md border p-3">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    <div>
                      <p className="font-medium text-sm">{parsedFile.filename}</p>
                      <Badge variant="secondary" className="mt-1">
                        {parsedFile.type && fileTypeLabels[parsedFile.type]}
                      </Badge>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setParsedFile(null);
                      fileInputRef.current?.click();
                    }}
                  >
                    Change
                  </Button>
                </div>

                {/* Scenario Metadata Preview */}
                {parsedFile.type === 'scenario' && parsedFile.metadata && (
                  <div className="rounded-md bg-muted/50 p-3 text-sm space-y-1">
                    <p><span className="text-muted-foreground">Version:</span> {parsedFile.metadata.ues_version}</p>
                    <p><span className="text-muted-foreground">Created:</span> {new Date(parsedFile.metadata.created_at).toLocaleString()}</p>
                    {parsedFile.metadata.author && (
                      <p><span className="text-muted-foreground">Author:</span> {parsedFile.metadata.author}</p>
                    )}
                    {parsedFile.metadata.description && (
                      <p><span className="text-muted-foreground">Description:</span> {parsedFile.metadata.description}</p>
                    )}
                  </div>
                )}

                <Separator />

                {/* Import Options */}
                <div className="space-y-4">
                  <Label className="text-sm font-medium">Import Options</Label>

                  {/* Environment-specific options */}
                  {(parsedFile.type === 'environment' || parsedFile.type === 'scenario') && (
                    <div className="space-y-3">
                      <div className="space-y-2">
                        <Label htmlFor="historic-handling" className="text-xs text-muted-foreground">
                          Historic Event Handling
                        </Label>
                        <Select
                          value={historicEventHandling}
                          onValueChange={(v) => setHistoricEventHandling(v as HistoricEventHandling)}
                        >
                          <SelectTrigger id="historic-handling">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="ignore">
                              Ignore (leave in queue)
                            </SelectItem>
                            <SelectItem value="delete">
                              Delete (remove from queue)
                            </SelectItem>
                            <SelectItem value="apply">
                              Apply (execute immediately)
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        <p className="text-xs text-muted-foreground">
                          How to handle existing events scheduled before the loaded environment&apos;s time
                        </p>
                      </div>

                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="strict-modalities"
                          checked={strictModalities}
                          onCheckedChange={(checked) => setStrictModalities(checked === true)}
                        />
                        <Label htmlFor="strict-modalities" className="text-sm cursor-pointer">
                          Strict mode (fail on unknown modalities)
                        </Label>
                      </div>
                    </div>
                  )}

                  {/* Events-specific options */}
                  {parsedFile.type === 'events' && (
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="merge-events"
                        checked={mergeEvents}
                        onCheckedChange={(checked) => setMergeEvents(checked === true)}
                      />
                      <Label htmlFor="merge-events" className="text-sm cursor-pointer">
                        Merge with existing events (instead of replace)
                      </Label>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button
              onClick={handleImport}
              disabled={!parsedFile || isImporting || isSimulationRunning}
            >
              {isImporting ? (
                <>Importing...</>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Import
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <CompatibilityDialog
        open={showCompatibilityDialog}
        onOpenChange={setShowCompatibilityDialog}
        warnings={compatibilityWarnings}
        onConfirm={handleCompatibilityConfirm}
      />
    </>
  );
}
