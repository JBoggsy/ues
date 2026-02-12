/**
 * Contact list component for the Contacts viewer.
 * Displays all contacts with filtering and selection.
 */
import { useMemo, useState } from 'react';
import { formatDistanceToNow, parseISO } from 'date-fns';
import {
  User,
  Star,
  Ban,
  Search,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type {
  ContactsState,
  Contact,
  ContactFilter,
  ContactSort,
  ContactDisplayItem,
} from './types';
import {
  resolveDisplayName,
  getPrimaryIdentifier,
  buildSubtitle,
} from './types';

interface ContactListProps {
  contactsState: ContactsState | null;
  selectedContactId: string | null;
  filter: ContactFilter;
  onFilterChange: (filter: ContactFilter) => void;
  onContactSelect: (contactId: string) => void;
}

/**
 * Build display items for contacts with computed display properties.
 */
function buildContactDisplayItems(
  contactsState: ContactsState
): ContactDisplayItem[] {
  const items: ContactDisplayItem[] = [];

  for (const contact of Object.values(contactsState.contacts)) {
    items.push({
      contact,
      displayName: resolveDisplayName(contact),
      subtitle: buildSubtitle(contact),
      primaryIdentifier: getPrimaryIdentifier(contact),
      groupCount: contact.groups.length,
      identifierCount: contact.identifiers.length,
    });
  }

  return items;
}

/**
 * Filter contacts based on selected filter.
 */
function filterContacts(
  items: ContactDisplayItem[],
  filter: ContactFilter
): ContactDisplayItem[] {
  switch (filter) {
    case 'favorites':
      return items.filter(item => item.contact.is_favorite);
    case 'blocked':
      return items.filter(item => item.contact.is_blocked);
    case 'recent':
      // Sort by updated_at descending and take top 20
      return [...items]
        .sort((a, b) =>
          new Date(b.contact.updated_at).getTime() -
          new Date(a.contact.updated_at).getTime()
        )
        .slice(0, 20);
    case 'all':
    default:
      return items;
  }
}

/**
 * Sort contacts by the selected sort option.
 */
function sortContacts(
  items: ContactDisplayItem[],
  sort: ContactSort
): ContactDisplayItem[] {
  return [...items].sort((a, b) => {
    switch (sort) {
      case 'name':
        return a.displayName.localeCompare(b.displayName);
      case 'updated':
        return (
          new Date(b.contact.updated_at).getTime() -
          new Date(a.contact.updated_at).getTime()
        );
      case 'created':
        return (
          new Date(b.contact.created_at).getTime() -
          new Date(a.contact.created_at).getTime()
        );
      default:
        return a.displayName.localeCompare(b.displayName);
    }
  });
}

/**
 * Search contacts by name or identifier value.
 */
function searchContacts(
  items: ContactDisplayItem[],
  query: string
): ContactDisplayItem[] {
  const lowerQuery = query.toLowerCase();
  return items.filter(item => {
    const c = item.contact;
    // Search display name
    if (item.displayName.toLowerCase().includes(lowerQuery)) return true;
    // Search first/last/nickname
    if (c.first_name?.toLowerCase().includes(lowerQuery)) return true;
    if (c.last_name?.toLowerCase().includes(lowerQuery)) return true;
    if (c.nickname?.toLowerCase().includes(lowerQuery)) return true;
    // Search identifiers
    if (c.identifiers.some(id => id.value.toLowerCase().includes(lowerQuery))) return true;
    // Search company
    if (c.company?.toLowerCase().includes(lowerQuery)) return true;
    return false;
  });
}

/**
 * Single contact list item with avatar, name, and metadata.
 */
function ContactItem({
  item,
  isSelected,
  onClick,
}: {
  item: ContactDisplayItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  const { contact } = item;

  // Generate initials for avatar
  const initials = (() => {
    if (contact.first_name && contact.last_name) {
      return `${contact.first_name[0]}${contact.last_name[0]}`.toUpperCase();
    }
    if (contact.first_name) return contact.first_name[0].toUpperCase();
    if (contact.last_name) return contact.last_name[0].toUpperCase();
    if (contact.display_name) return contact.display_name[0].toUpperCase();
    return '?';
  })();

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left p-3 border-b transition-colors',
        'hover:bg-muted/50',
        isSelected && 'bg-muted',
        contact.is_blocked && 'opacity-50'
      )}
    >
      <div className="flex items-center gap-3">
        {/* Avatar */}
        <div
          className={cn(
            'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium',
            contact.is_favorite
              ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
              : 'bg-muted text-muted-foreground'
          )}
        >
          {contact.photo_url ? (
            <img
              src={contact.photo_url}
              alt={item.displayName}
              className="w-10 h-10 rounded-full object-cover"
            />
          ) : (
            initials
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Name row with badges */}
          <div className="flex items-center gap-1.5">
            <span
              className={cn(
                'font-medium truncate text-sm',
                contact.is_favorite && 'font-semibold'
              )}
            >
              {item.displayName}
            </span>
            {contact.is_favorite && (
              <Star className="h-3 w-3 text-yellow-500 flex-shrink-0 fill-yellow-500" />
            )}
            {contact.is_blocked && (
              <Ban className="h-3 w-3 text-destructive flex-shrink-0" />
            )}
          </div>

          {/* Subtitle */}
          {item.subtitle && (
            <div className="text-xs text-muted-foreground truncate mt-0.5">
              {item.subtitle}
            </div>
          )}
        </div>

        {/* Right side — group count */}
        {item.groupCount > 0 && (
          <div className="flex-shrink-0">
            <Badge variant="secondary" className="text-xs">
              <Users className="h-3 w-3 mr-1" />
              {item.groupCount}
            </Badge>
          </div>
        )}
      </div>
    </button>
  );
}

export function ContactList({
  contactsState,
  selectedContactId,
  filter,
  onFilterChange,
  onContactSelect,
}: ContactListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sort, setSort] = useState<ContactSort>('name');

  // Build, filter, search, and sort contact items
  const displayItems = useMemo(() => {
    if (!contactsState) return [];
    let items = buildContactDisplayItems(contactsState);
    items = filterContacts(items, filter);
    if (searchQuery.trim()) {
      items = searchContacts(items, searchQuery.trim());
    }
    items = sortContacts(items, sort);
    return items;
  }, [contactsState, filter, searchQuery, sort]);

  // Count favorites for filter badge
  const favoritesCount = useMemo(() => {
    return contactsState?.favorites_count ?? 0;
  }, [contactsState]);

  if (!contactsState) {
    return (
      <div className="w-80 border-r bg-background flex items-center justify-center">
        <span className="text-muted-foreground">Loading...</span>
      </div>
    );
  }

  return (
    <div className="w-80 border-r bg-background flex flex-col">
      {/* Search bar */}
      <div className="p-2 border-b">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search contacts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9"
          />
        </div>
      </div>

      {/* Filter and sort row */}
      <div className="flex gap-2 p-2 border-b">
        <Select
          value={filter}
          onValueChange={(v) => onFilterChange(v as ContactFilter)}
        >
          <SelectTrigger className="flex-1 h-8 text-xs">
            <SelectValue placeholder="Filter" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Contacts</SelectItem>
            <SelectItem value="favorites">
              Favorites {favoritesCount > 0 && `(${favoritesCount})`}
            </SelectItem>
            <SelectItem value="blocked">Blocked</SelectItem>
            <SelectItem value="recent">Recent</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={sort}
          onValueChange={(v) => setSort(v as ContactSort)}
        >
          <SelectTrigger className="w-28 h-8 text-xs">
            <SelectValue placeholder="Sort" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="name">By Name</SelectItem>
            <SelectItem value="updated">By Updated</SelectItem>
            <SelectItem value="created">By Created</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Contact list */}
      <ScrollArea className="flex-1">
        {displayItems.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground text-sm">
            {searchQuery
              ? 'No contacts match your search'
              : filter === 'all'
                ? 'No contacts yet'
                : filter === 'favorites'
                  ? 'No favorite contacts'
                  : filter === 'blocked'
                    ? 'No blocked contacts'
                    : 'No recent contacts'}
          </div>
        ) : (
          displayItems.map((item) => (
            <ContactItem
              key={item.contact.contact_id}
              item={item}
              isSelected={item.contact.contact_id === selectedContactId}
              onClick={() => onContactSelect(item.contact.contact_id)}
            />
          ))
        )}
      </ScrollArea>
    </div>
  );
}
