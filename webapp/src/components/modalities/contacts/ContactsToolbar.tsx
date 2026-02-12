/**
 * Toolbar component for the Contacts viewer.
 * Provides action buttons for contact management.
 */
import {
  UserPlus,
  Star,
  StarOff,
  Ban,
  ShieldCheck,
  Trash2,
  RefreshCw,
  Users,
  Merge,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { Contact } from './types';

interface ContactsToolbarProps {
  selectedContact: Contact | null;
  onCreateContact: () => void;
  onDelete: () => void;
  onFavorite: () => void;
  onUnfavorite: () => void;
  onBlock: () => void;
  onUnblock: () => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

export function ContactsToolbar({
  selectedContact,
  onCreateContact,
  onDelete,
  onFavorite,
  onUnfavorite,
  onBlock,
  onUnblock,
  onRefresh,
  isRefreshing,
}: ContactsToolbarProps) {
  const hasSelection = !!selectedContact;
  const isFavorite = selectedContact?.is_favorite ?? false;
  const isBlocked = selectedContact?.is_blocked ?? false;

  return (
    <div className="flex items-center gap-1 px-2 py-1.5 border-b bg-background">
      {/* New Contact Button */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="sm" onClick={onCreateContact}>
              <UserPlus className="h-4 w-4 mr-2" />
              New Contact
            </Button>
          </TooltipTrigger>
          <TooltipContent>Create a new contact</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <Separator orientation="vertical" className="h-6 mx-1" />

      {/* Contact actions — only enabled with selection */}

      {/* Favorite / Unfavorite */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={isFavorite ? onUnfavorite : onFavorite}
              disabled={!hasSelection}
            >
              {isFavorite ? (
                <StarOff className="h-4 w-4" />
              ) : (
                <Star className="h-4 w-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            {isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Block / Unblock */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={isBlocked ? onUnblock : onBlock}
              disabled={!hasSelection}
            >
              {isBlocked ? (
                <ShieldCheck className="h-4 w-4" />
              ) : (
                <Ban className="h-4 w-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            {isBlocked ? 'Unblock contact' : 'Block contact'}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Delete */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onDelete}
              disabled={!hasSelection}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Delete contact</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Refresh */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onRefresh}
            >
              <RefreshCw
                className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`}
              />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Refresh contacts</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}
