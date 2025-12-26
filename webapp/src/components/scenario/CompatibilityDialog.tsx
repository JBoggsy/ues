/**
 * Compatibility Dialog component for handling import warnings.
 * 
 * Displayed when loading a scenario with unknown modalities or other
 * compatibility issues. Allows users to proceed with partial import
 * or cancel the operation.
 */
import { AlertTriangle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

interface CompatibilityDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  warnings: string[];
  onConfirm: () => void;
}

export function CompatibilityDialog({
  open,
  onOpenChange,
  warnings,
  onConfirm,
}: CompatibilityDialogProps) {
  const handleConfirm = () => {
    onConfirm();
    onOpenChange(false);
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-amber-600 dark:text-amber-500">
            <AlertTriangle className="h-5 w-5" />
            Compatibility Warning
          </DialogTitle>
          <DialogDescription>
            The file contains data that may not be fully compatible with this version of UES.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <p className="text-sm mb-3">
            The following issues were detected:
          </p>
          
          <ScrollArea className="h-[150px] rounded-md border p-3">
            <ul className="space-y-2">
              {warnings.map((warning, index) => (
                <li
                  key={index}
                  className="text-sm text-muted-foreground flex items-start gap-2"
                >
                  <span className="text-amber-500 mt-0.5">•</span>
                  <span>{warning}</span>
                </li>
              ))}
            </ul>
          </ScrollArea>

          <p className="text-sm text-muted-foreground mt-4">
            You can proceed with loading only the compatible parts of the file,
            or cancel to preserve your current state.
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <Button
            variant="default"
            onClick={handleConfirm}
            className="bg-amber-600 hover:bg-amber-700"
          >
            Load Compatible Only
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
