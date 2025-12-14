/**
 * Email toolbar component.
 * Provides action buttons for email operations.
 */
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  PenSquare,
  Reply,
  ReplyAll,
  Forward,
  Trash2,
  Archive,
  Star,
  Mail,
  MailOpen,
  FolderInput,
  MoreHorizontal,
  AlertOctagon,
  RefreshCw,
} from 'lucide-react';

interface EmailToolbarProps {
  hasSelection: boolean;
  hasEmailSelected: boolean;
  isStarred: boolean;
  isRead: boolean;
  onCompose: () => void;
  onReply: () => void;
  onReplyAll: () => void;
  onForward: () => void;
  onDelete: () => void;
  onArchive: () => void;
  onToggleStar: () => void;
  onToggleRead: () => void;
  onMarkSpam: () => void;
  onMoveToFolder: (folder: string) => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

/**
 * Action button with tooltip.
 */
function ToolbarButton({
  icon: Icon,
  label,
  onClick,
  disabled,
  variant = 'ghost',
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  variant?: 'ghost' | 'default' | 'outline';
}) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant}
            size="sm"
            onClick={onClick}
            disabled={disabled}
            className="h-8"
          >
            <Icon className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{label}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function EmailToolbar({
  hasSelection,
  hasEmailSelected,
  isStarred,
  isRead,
  onCompose,
  onReply,
  onReplyAll,
  onForward,
  onDelete,
  onArchive,
  onToggleStar,
  onToggleRead,
  onMarkSpam,
  onMoveToFolder,
  onRefresh,
  isRefreshing,
}: EmailToolbarProps) {
  return (
    <div className="flex items-center gap-1 p-2 border-b bg-muted/30">
      {/* Compose Button - Always enabled */}
      <Button
        variant="default"
        size="sm"
        onClick={onCompose}
        className="h-8 gap-2"
      >
        <PenSquare className="h-4 w-4" />
        <span className="hidden sm:inline">Compose</span>
      </Button>

      <Separator orientation="vertical" className="h-6 mx-2" />

      {/* Reply Actions - Need email selected */}
      <ToolbarButton
        icon={Reply}
        label="Reply"
        onClick={onReply}
        disabled={!hasEmailSelected}
      />
      <ToolbarButton
        icon={ReplyAll}
        label="Reply All"
        onClick={onReplyAll}
        disabled={!hasEmailSelected}
      />
      <ToolbarButton
        icon={Forward}
        label="Forward"
        onClick={onForward}
        disabled={!hasEmailSelected}
      />

      <Separator orientation="vertical" className="h-6 mx-2" />

      {/* Organization Actions - Need selection */}
      <ToolbarButton
        icon={Archive}
        label="Archive"
        onClick={onArchive}
        disabled={!hasSelection}
      />
      <ToolbarButton
        icon={Trash2}
        label="Delete"
        onClick={onDelete}
        disabled={!hasSelection}
      />
      <ToolbarButton
        icon={isStarred ? Star : Star}
        label={isStarred ? 'Unstar' : 'Star'}
        onClick={onToggleStar}
        disabled={!hasSelection}
      />
      <ToolbarButton
        icon={isRead ? MailOpen : Mail}
        label={isRead ? 'Mark Unread' : 'Mark Read'}
        onClick={onToggleRead}
        disabled={!hasSelection}
      />

      {/* More Actions Dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            disabled={!hasSelection}
            className="h-8"
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={onMarkSpam}>
            <AlertOctagon className="h-4 w-4 mr-2" />
            Mark as Spam
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => onMoveToFolder('inbox')}>
            <FolderInput className="h-4 w-4 mr-2" />
            Move to Inbox
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => onMoveToFolder('archive')}>
            <Archive className="h-4 w-4 mr-2" />
            Move to Archive
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => onMoveToFolder('trash')}>
            <Trash2 className="h-4 w-4 mr-2" />
            Move to Trash
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Refresh */}
      <ToolbarButton
        icon={RefreshCw}
        label="Refresh"
        onClick={onRefresh}
        disabled={isRefreshing}
      />
    </div>
  );
}
