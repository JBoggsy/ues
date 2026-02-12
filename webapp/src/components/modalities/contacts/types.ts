/**
 * Type definitions for the Contacts Viewer component.
 * These match the backend Contacts state models with UI-specific extensions.
 */

/**
 * A single identifier (phone number, email, handle) for a contact.
 */
export interface ContactIdentifier {
  identifier_type: string;
  value: string;
  label?: string | null;
}

/**
 * A physical mailing address for a contact.
 */
export interface PostalAddress {
  street?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  label?: string | null;
}

/**
 * A single contact entry in the address book.
 */
export interface Contact {
  contact_id: string;
  first_name?: string | null;
  last_name?: string | null;
  display_name?: string | null;
  nickname?: string | null;
  identifiers: ContactIdentifier[];
  company?: string | null;
  job_title?: string | null;
  addresses: PostalAddress[];
  birthday?: string | null;
  notes?: string | null;
  photo_url?: string | null;
  is_favorite: boolean;
  is_blocked: boolean;
  groups: string[];
  created_at: string;
  updated_at: string;
}

/**
 * Complete contacts state from the backend (GET /contacts/state).
 */
export interface ContactsState {
  modality_type: 'contacts';
  current_time: string;
  contacts: Record<string, Contact>;
  total_count: number;
  favorites_count: number;
  blocked_count: number;
  groups: string[];
}

/**
 * Filter options for the contacts list.
 */
export type ContactFilter = 'all' | 'favorites' | 'blocked' | 'recent';

/**
 * Sort options for the contacts list.
 */
export type ContactSort = 'name' | 'updated' | 'created';

/**
 * Display item for the contact list.
 * Extends contact data with computed display properties.
 */
export interface ContactDisplayItem {
  contact: Contact;
  displayName: string;
  subtitle: string;
  primaryIdentifier: string;
  groupCount: number;
  identifierCount: number;
}

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

/**
 * Resolve the best display name for a contact, mirroring the server's
 * Contact.get_resolved_display_name() logic.
 *
 * Resolution order:
 * 1. display_name
 * 2. "First Last"
 * 3. nickname
 * 4. First identifier value
 * 5. "Unknown"
 */
export function resolveDisplayName(contact: Contact): string {
  if (contact.display_name) {
    return contact.display_name;
  }

  const nameParts: string[] = [];
  if (contact.first_name) nameParts.push(contact.first_name);
  if (contact.last_name) nameParts.push(contact.last_name);
  if (nameParts.length > 0) {
    return nameParts.join(' ');
  }

  if (contact.nickname) {
    return contact.nickname;
  }

  if (contact.identifiers.length > 0) {
    return contact.identifiers[0].value;
  }

  return 'Unknown';
}

/**
 * Get the primary identifier string for a contact (phone or email preferred).
 */
export function getPrimaryIdentifier(contact: Contact): string {
  if (contact.identifiers.length === 0) return '';

  // Prefer phone, then email, then first identifier
  const phone = contact.identifiers.find(id => id.identifier_type === 'phone');
  if (phone) return phone.value;

  const email = contact.identifiers.find(id => id.identifier_type === 'email');
  if (email) return email.value;

  return contact.identifiers[0].value;
}

/**
 * Build a subtitle string for a contact (company + job title, or identifier type).
 */
export function buildSubtitle(contact: Contact): string {
  const parts: string[] = [];

  if (contact.job_title) parts.push(contact.job_title);
  if (contact.company) parts.push(contact.company);

  if (parts.length > 0) {
    return parts.join(' at ');
  }

  // Fall back to primary identifier type
  if (contact.identifiers.length > 0) {
    const primary = contact.identifiers[0];
    const label = primary.label || primary.identifier_type;
    return `${label}: ${primary.value}`;
  }

  return '';
}

/**
 * Format a postal address as a single-line string, mirroring the server's
 * PostalAddress.format_oneline() method.
 */
export function formatAddressOneline(address: PostalAddress): string {
  const parts: string[] = [];

  if (address.street) parts.push(address.street);
  if (address.city) parts.push(address.city);
  if (address.state) parts.push(address.state);
  if (address.postal_code) parts.push(address.postal_code);
  if (address.country) parts.push(address.country);

  return parts.join(', ');
}

/**
 * Format an identifier type for display (capitalize, handle common types).
 */
export function formatIdentifierType(identifierType: string): string {
  const typeMap: Record<string, string> = {
    phone: 'Phone',
    email: 'Email',
    discord: 'Discord',
    twitter: 'Twitter',
    github: 'GitHub',
    linkedin: 'LinkedIn',
    slack: 'Slack',
  };
  return typeMap[identifierType.toLowerCase()] || identifierType;
}
