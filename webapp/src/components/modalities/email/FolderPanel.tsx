/**
 * Folder panel component for the email viewer.
 * Displays standard folders and custom labels with unread counts.
 */
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import {
  Inbox,
  Send,
  FileEdit,
  Trash2,
  AlertOctagon,
  Archive,
  Tag,
  Plus,
} from 'lucide-react';
import type { EmailState } from './types';

interface FolderPanelProps {
  emailState: EmailState | null;
  selectedFolder: string;
  onFolderSelect: (folder: string) => void;
  selectedLabel: string | null;
  onLabelSelect: (label: string | null) => void;
}

/**
 * Standard folder configuration with icons.
 */
const STANDARD_FOLDERS = [
  { name: 'inbox', label: 'Inbox', icon: Inbox },
  { name: 'sent', label: 'Sent', icon: Send },
  { name: 'drafts', label: 'Drafts', icon: FileEdit },
  { name: 'trash', label: 'Trash', icon: Trash2 },
  { name: 'spam', label: 'Spam', icon: AlertOctagon },
  { name: 'archive', label: 'Archive', icon: Archive },
];

/**
 * Get unread count for a folder.
 */
function getFolderUnreadCount(
  emailState: EmailState | null,
  folderName: string
): number {
  if (!emailState?.folders || !emailState?.emails) return 0;
  
  const messageIds = emailState.folders[folderName] || [];
  return messageIds.filter((id) => {
    const email = emailState.emails[id];
    return email && !email.is_read;
  }).length;
}

/**
 * Get total count for a folder.
 */
function getFolderCount(
  emailState: EmailState | null,
  folderName: string
): number {
  if (!emailState?.folders) return 0;
  return (emailState.folders[folderName] || []).length;
}

/**
 * Get count for a label.
 */
function getLabelCount(
  emailState: EmailState | null,
  labelName: string
): number {
  if (!emailState?.labels) return 0;
  return (emailState.labels[labelName] || []).length;
}

export function FolderPanel({
  emailState,
  selectedFolder,
  onFolderSelect,
  selectedLabel,
  onLabelSelect,
}: FolderPanelProps) {
  const customLabels = emailState?.labels
    ? Object.keys(emailState.labels).filter(
        (label) => !STANDARD_FOLDERS.some((f) => f.name === label)
      )
    : [];

  return (
    <div className="w-48 border-r bg-muted/20 flex flex-col h-full">
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {/* Standard Folders */}
          {STANDARD_FOLDERS.map((folder) => {
            const Icon = folder.icon;
            const count = getFolderCount(emailState, folder.name);
            const unreadCount = getFolderUnreadCount(emailState, folder.name);
            const isSelected = selectedFolder === folder.name && !selectedLabel;

            return (
              <button
                key={folder.name}
                onClick={() => {
                  onFolderSelect(folder.name);
                  onLabelSelect(null);
                }}
                className={cn(
                  'w-full flex items-center justify-between gap-2 px-3 py-2 text-sm rounded-md transition-colors',
                  isSelected
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-muted text-foreground'
                )}
              >
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  <span>{folder.label}</span>
                </div>
                {unreadCount > 0 ? (
                  <Badge
                    variant={isSelected ? 'secondary' : 'default'}
                    className="h-5 min-w-5 text-xs"
                  >
                    {unreadCount}
                  </Badge>
                ) : count > 0 ? (
                  <span className="text-xs text-muted-foreground">
                    {count}
                  </span>
                ) : null}
              </button>
            );
          })}

          {/* Labels Section */}
          {customLabels.length > 0 && (
            <>
              <Separator className="my-2" />
              <p className="px-3 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Labels
              </p>
              {customLabels.map((label) => {
                const count = getLabelCount(emailState, label);
                const isSelected = selectedLabel === label;

                return (
                  <button
                    key={label}
                    onClick={() => {
                      onLabelSelect(label);
                    }}
                    className={cn(
                      'w-full flex items-center justify-between gap-2 px-3 py-2 text-sm rounded-md transition-colors',
                      isSelected
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-muted text-foreground'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Tag className="h-4 w-4" />
                      <span className="truncate">{label}</span>
                    </div>
                    {count > 0 && (
                      <span className="text-xs text-muted-foreground">
                        {count}
                      </span>
                    )}
                  </button>
                );
              })}
            </>
          )}
        </div>
      </ScrollArea>

      {/* Add Label Button */}
      <div className="p-2 border-t">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 text-muted-foreground"
          disabled
          title="Label management coming soon"
        >
          <Plus className="h-4 w-4" />
          Add Label
        </Button>
      </div>
    </div>
  );
}
