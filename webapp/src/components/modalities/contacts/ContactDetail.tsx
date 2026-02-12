/**
 * Contact detail component for the Contacts viewer.
 * Displays expanded information for a selected contact.
 */
import { formatDistanceToNow, parseISO } from 'date-fns';
import {
  User,
  Phone,
  Mail,
  MapPin,
  Building2,
  Briefcase,
  Star,
  Ban,
  Users,
  Cake,
  StickyNote,
  Link,
  Clock,
  Hash,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import type { Contact, ContactIdentifier, PostalAddress } from './types';
import {
  resolveDisplayName,
  formatAddressOneline,
  formatIdentifierType,
} from './types';

interface ContactDetailProps {
  contact: Contact | null;
}

/**
 * Get the appropriate icon for an identifier type.
 */
function identifierIcon(identifierType: string) {
  switch (identifierType.toLowerCase()) {
    case 'phone':
      return Phone;
    case 'email':
      return Mail;
    default:
      return Hash;
  }
}

/**
 * Section header with icon.
 */
function SectionHeader({
  icon: Icon,
  title,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <span className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
        {title}
      </span>
    </div>
  );
}

/**
 * Render a single identifier row.
 */
function IdentifierRow({ identifier }: { identifier: ContactIdentifier }) {
  const Icon = identifierIcon(identifier.identifier_type);

  return (
    <div className="flex items-center gap-3 py-1.5">
      <Icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-sm">{identifier.value}</div>
        <div className="text-xs text-muted-foreground">
          {formatIdentifierType(identifier.identifier_type)}
          {identifier.label && ` · ${identifier.label}`}
        </div>
      </div>
    </div>
  );
}

/**
 * Render a single address row.
 */
function AddressRow({ address }: { address: PostalAddress }) {
  const formatted = formatAddressOneline(address);
  if (!formatted) return null;

  return (
    <div className="flex items-start gap-3 py-1.5">
      <MapPin className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="text-sm">{formatted}</div>
        {address.label && (
          <div className="text-xs text-muted-foreground">{address.label}</div>
        )}
      </div>
    </div>
  );
}

export function ContactDetail({ contact }: ContactDetailProps) {
  if (!contact) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <User className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Select a contact to view details</p>
        </div>
      </div>
    );
  }

  const displayName = resolveDisplayName(contact);

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

  // Format timestamps
  let createdAgo = '';
  let updatedAgo = '';
  try {
    createdAgo = formatDistanceToNow(parseISO(contact.created_at), {
      addSuffix: true,
    });
    updatedAgo = formatDistanceToNow(parseISO(contact.updated_at), {
      addSuffix: true,
    });
  } catch {
    // ignore parse errors
  }

  return (
    <div className="flex-1 flex flex-col min-w-0">
      <ScrollArea className="flex-1">
        <div className="p-6 max-w-2xl">
          {/* Header — Avatar + Name + Status badges */}
          <div className="flex items-start gap-4 mb-6">
            <div
              className={cn(
                'flex-shrink-0 w-16 h-16 rounded-full flex items-center justify-center text-xl font-semibold',
                contact.is_favorite
                  ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                  : 'bg-muted text-muted-foreground'
              )}
            >
              {contact.photo_url ? (
                <img
                  src={contact.photo_url}
                  alt={displayName}
                  className="w-16 h-16 rounded-full object-cover"
                />
              ) : (
                initials
              )}
            </div>

            <div className="flex-1 min-w-0">
              <h2 className="text-xl font-semibold truncate">{displayName}</h2>

              {/* Show name parts if different from display_name */}
              {contact.display_name && (contact.first_name || contact.last_name) && (
                <div className="text-sm text-muted-foreground">
                  {[contact.first_name, contact.last_name]
                    .filter(Boolean)
                    .join(' ')}
                </div>
              )}

              {contact.nickname && (
                <div className="text-sm text-muted-foreground italic">
                  "{contact.nickname}"
                </div>
              )}

              {/* Status badges */}
              <div className="flex items-center gap-2 mt-2">
                {contact.is_favorite && (
                  <Badge
                    variant="secondary"
                    className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                  >
                    <Star className="h-3 w-3 mr-1 fill-yellow-500 text-yellow-500" />
                    Favorite
                  </Badge>
                )}
                {contact.is_blocked && (
                  <Badge variant="destructive">
                    <Ban className="h-3 w-3 mr-1" />
                    Blocked
                  </Badge>
                )}
                {contact.groups.length > 0 &&
                  contact.groups.map((group) => (
                    <Badge key={group} variant="outline">
                      <Users className="h-3 w-3 mr-1" />
                      {group}
                    </Badge>
                  ))}
              </div>
            </div>
          </div>

          <Separator className="mb-6" />

          {/* Identifiers section */}
          {contact.identifiers.length > 0 && (
            <div className="mb-6">
              <SectionHeader icon={Link} title="Identifiers" />
              <div className="space-y-0.5">
                {contact.identifiers.map((identifier, idx) => (
                  <IdentifierRow key={idx} identifier={identifier} />
                ))}
              </div>
            </div>
          )}

          {/* Work / Organization section */}
          {(contact.company || contact.job_title) && (
            <div className="mb-6">
              <SectionHeader icon={Building2} title="Work" />
              <div className="space-y-1">
                {contact.job_title && (
                  <div className="flex items-center gap-3 py-1">
                    <Briefcase className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="text-sm">{contact.job_title}</span>
                  </div>
                )}
                {contact.company && (
                  <div className="flex items-center gap-3 py-1">
                    <Building2 className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="text-sm">{contact.company}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Addresses section */}
          {contact.addresses.length > 0 && (
            <div className="mb-6">
              <SectionHeader icon={MapPin} title="Addresses" />
              <div className="space-y-0.5">
                {contact.addresses.map((address, idx) => (
                  <AddressRow key={idx} address={address} />
                ))}
              </div>
            </div>
          )}

          {/* Birthday */}
          {contact.birthday && (
            <div className="mb-6">
              <SectionHeader icon={Cake} title="Birthday" />
              <div className="text-sm pl-6">{String(contact.birthday)}</div>
            </div>
          )}

          {/* Notes */}
          {contact.notes && (
            <div className="mb-6">
              <SectionHeader icon={StickyNote} title="Notes" />
              <div className="text-sm pl-6 whitespace-pre-wrap">
                {contact.notes}
              </div>
            </div>
          )}

          {/* Metadata */}
          <Separator className="mb-4" />
          <div className="text-xs text-muted-foreground space-y-1">
            <div className="flex items-center gap-2">
              <Clock className="h-3 w-3" />
              <span>Created {createdAgo}</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-3 w-3" />
              <span>Updated {updatedAgo}</span>
            </div>
            <div className="flex items-center gap-2">
              <Hash className="h-3 w-3" />
              <span className="font-mono text-[10px]">{contact.contact_id}</span>
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
