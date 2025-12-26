/**
 * Export Dialog component for saving simulation state to files.
 * 
 * Allows users to export:
 * - Environment only (.ues-env.json)
 * - Events only (.ues-events.json)
 * - Full scenario with metadata (.ues-scenario.json)
 */
import { useState } from 'react';
import { Download, FileJson, Calendar, Layers } from 'lucide-react';
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
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import {
  useExportEnvironment,
  useExportEvents,
  useExportScenario,
  downloadJsonFile,
  generateExportFilename,
} from '@/api';
import type { ExportType } from '@/api/types/scenario';
import { EXPORT_TYPE_LABELS } from '@/api/types/scenario';

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ExportDialog({ open, onOpenChange }: ExportDialogProps) {
  const [exportType, setExportType] = useState<ExportType>('scenario');
  const [author, setAuthor] = useState('');
  const [description, setDescription] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  const exportEnvironment = useExportEnvironment();
  const exportEvents = useExportEvents();
  const exportScenario = useExportScenario();

  const handleExport = async () => {
    setIsExporting(true);
    
    try {
      let content: string;
      let filename: string;

      switch (exportType) {
        case 'environment': {
          const result = await exportEnvironment.mutateAsync();
          content = JSON.stringify(result.environment, null, 2);
          filename = generateExportFilename('environment');
          toast.success(`Exported ${result.modalities_exported.length} modalities`);
          break;
        }
        case 'events': {
          const result = await exportEvents.mutateAsync();
          content = JSON.stringify(result.events, null, 2);
          filename = generateExportFilename('events');
          toast.success(`Exported ${result.total_events} events (${result.pending_events} pending)`);
          break;
        }
        case 'scenario': {
          const result = await exportScenario.mutateAsync({
            author: author || undefined,
            description: description || undefined,
          });
          content = JSON.stringify(result.scenario, null, 2);
          filename = generateExportFilename('scenario');
          toast.success('Scenario exported successfully');
          break;
        }
      }

      downloadJsonFile(content, filename);
      onOpenChange(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Export failed';
      toast.error(message);
    } finally {
      setIsExporting(false);
    }
  };

  const handleClose = () => {
    // Reset form state when closing
    setExportType('scenario');
    setAuthor('');
    setDescription('');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Export Simulation State
          </DialogTitle>
          <DialogDescription>
            Save the current simulation state to a JSON file for backup or sharing.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Export Type Selection */}
          <div className="space-y-3">
            <Label>Export Type</Label>
            <RadioGroup
              value={exportType}
              onValueChange={(value) => setExportType(value as ExportType)}
              className="space-y-2"
            >
              <div className="flex items-center space-x-3 rounded-md border p-3 hover:bg-muted/50">
                <RadioGroupItem value="scenario" id="scenario" />
                <Label htmlFor="scenario" className="flex-1 cursor-pointer">
                  <div className="flex items-center gap-2">
                    <Layers className="h-4 w-4 text-muted-foreground" />
                    <span>{EXPORT_TYPE_LABELS.scenario}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Complete simulation state with metadata, environment, and events
                  </p>
                </Label>
              </div>

              <div className="flex items-center space-x-3 rounded-md border p-3 hover:bg-muted/50">
                <RadioGroupItem value="environment" id="environment" />
                <Label htmlFor="environment" className="flex-1 cursor-pointer">
                  <div className="flex items-center gap-2">
                    <FileJson className="h-4 w-4 text-muted-foreground" />
                    <span>{EXPORT_TYPE_LABELS.environment}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Current modality states and simulator time
                  </p>
                </Label>
              </div>

              <div className="flex items-center space-x-3 rounded-md border p-3 hover:bg-muted/50">
                <RadioGroupItem value="events" id="events" />
                <Label htmlFor="events" className="flex-1 cursor-pointer">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span>{EXPORT_TYPE_LABELS.events}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    All events in the queue (pending, executed, etc.)
                  </p>
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Metadata fields for full scenario export */}
          {exportType === 'scenario' && (
            <>
              <Separator />
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="author">Author (optional)</Label>
                  <Input
                    id="author"
                    placeholder="Your name or identifier"
                    value={author}
                    onChange={(e) => setAuthor(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description (optional)</Label>
                  <Textarea
                    id="description"
                    placeholder="Brief description of this scenario..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                  />
                </div>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button onClick={handleExport} disabled={isExporting}>
            {isExporting ? (
              <>Exporting...</>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Export
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
