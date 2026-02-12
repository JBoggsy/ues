/**
 * Shared hook for looking up contacts from other modality viewers.
 *
 * This hook fetches the contacts state with a low-frequency poll and builds
 * efficient lookup indexes keyed by phone number and email address. Any
 * modality viewer can import this hook to resolve identifiers to display names.
 */
import { useMemo } from 'react';
import { useModalityState } from '@/api';
import type { ContactsState, Contact } from './types';
import { resolveDisplayName } from './types';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/**
 * Lightweight summary of a contact, suitable for display in other modalities.
 */
export interface ContactSummary {
  contact_id: string;
  display_name: string;
  first_name?: string | null;
  last_name?: string | null;
  is_favorite: boolean;
  is_blocked: boolean;
  photo_url?: string | null;
}

/**
 * An email contact entry for autocomplete use-cases.
 */
export interface EmailContactEntry {
  contact_id: string;
  display_name: string;
  email: string;
  label?: string | null;
}

/**
 * A phone contact entry for autocomplete use-cases.
 */
export interface PhoneContactEntry {
  contact_id: string;
  display_name: string;
  phone: string;
  label?: string | null;
}

/**
 * Return value of the `useContactsLookup` hook.
 */
export interface ContactsLookup {
  /** Resolve a phone number to a display name. Returns `undefined` if not found. */
  resolvePhone: (phoneNumber: string) => string | undefined;
  /** Resolve an email address to a display name. Returns `undefined` if not found. */
  resolveEmail: (email: string) => string | undefined;
  /** Get the full contact summary by phone number. */
  getContactByPhone: (phoneNumber: string) => ContactSummary | undefined;
  /** Get the full contact summary by email. */
  getContactByEmail: (email: string) => ContactSummary | undefined;
  /** All contacts that have at least one email identifier (for autocomplete pickers). */
  contactsWithEmail: EmailContactEntry[];
  /** All contacts that have at least one phone identifier (for autocomplete pickers). */
  contactsWithPhone: PhoneContactEntry[];
  /** All contacts (raw). */
  allContacts: Contact[];
  /** Whether the contacts state is currently loading. */
  isLoading: boolean;
  /** Whether the contacts modality has loaded data. */
  isAvailable: boolean;
}

// ---------------------------------------------------------------------------
// Hook implementation
// ---------------------------------------------------------------------------

/**
 * Build a `ContactSummary` from a full `Contact` object.
 */
function toSummary(contact: Contact): ContactSummary {
  return {
    contact_id: contact.contact_id,
    display_name: resolveDisplayName(contact),
    first_name: contact.first_name,
    last_name: contact.last_name,
    is_favorite: contact.is_favorite,
    is_blocked: contact.is_blocked,
    photo_url: contact.photo_url,
  };
}

/**
 * Hook that fetches contacts state and exposes efficient identifier lookups.
 *
 * Uses a moderate polling interval (10 s) to keep the contacts cache fresh
 * without unnecessarily hammering the server.
 */
export function useContactsLookup(): ContactsLookup {
  const {
    data: contactsState,
    isLoading,
  } = useModalityState<ContactsState>('contacts', 10_000);

  // Build index maps: identifier value → Contact
  const { phoneMap, emailMap } = useMemo(() => {
    const pm = new Map<string, Contact>();
    const em = new Map<string, Contact>();

    if (!contactsState) return { phoneMap: pm, emailMap: em };

    for (const contact of Object.values(contactsState.contacts)) {
      for (const ident of contact.identifiers) {
        const lower = ident.value.toLowerCase();
        if (ident.identifier_type === 'phone') {
          pm.set(ident.value, contact);    // phones are case-sensitive (digits)
        } else if (ident.identifier_type === 'email') {
          em.set(lower, contact);           // emails compared case-insensitively
        }
      }
    }

    return { phoneMap: pm, emailMap: em };
  }, [contactsState]);

  // Resolver functions (stable via useMemo)
  const resolvePhone = useMemo(
    () => (phoneNumber: string): string | undefined => {
      const contact = phoneMap.get(phoneNumber);
      return contact ? resolveDisplayName(contact) : undefined;
    },
    [phoneMap],
  );

  const resolveEmail = useMemo(
    () => (email: string): string | undefined => {
      const contact = emailMap.get(email.toLowerCase());
      return contact ? resolveDisplayName(contact) : undefined;
    },
    [emailMap],
  );

  const getContactByPhone = useMemo(
    () => (phoneNumber: string): ContactSummary | undefined => {
      const contact = phoneMap.get(phoneNumber);
      return contact ? toSummary(contact) : undefined;
    },
    [phoneMap],
  );

  const getContactByEmail = useMemo(
    () => (email: string): ContactSummary | undefined => {
      const contact = emailMap.get(email.toLowerCase());
      return contact ? toSummary(contact) : undefined;
    },
    [emailMap],
  );

  // Autocomplete lists
  const contactsWithEmail = useMemo((): EmailContactEntry[] => {
    if (!contactsState) return [];
    const entries: EmailContactEntry[] = [];
    for (const contact of Object.values(contactsState.contacts)) {
      for (const ident of contact.identifiers) {
        if (ident.identifier_type === 'email') {
          entries.push({
            contact_id: contact.contact_id,
            display_name: resolveDisplayName(contact),
            email: ident.value,
            label: ident.label,
          });
        }
      }
    }
    return entries;
  }, [contactsState]);

  const contactsWithPhone = useMemo((): PhoneContactEntry[] => {
    if (!contactsState) return [];
    const entries: PhoneContactEntry[] = [];
    for (const contact of Object.values(contactsState.contacts)) {
      for (const ident of contact.identifiers) {
        if (ident.identifier_type === 'phone') {
          entries.push({
            contact_id: contact.contact_id,
            display_name: resolveDisplayName(contact),
            phone: ident.value,
            label: ident.label,
          });
        }
      }
    }
    return entries;
  }, [contactsState]);

  const allContacts = useMemo(
    () => (contactsState ? Object.values(contactsState.contacts) : []),
    [contactsState],
  );

  return {
    resolvePhone,
    resolveEmail,
    getContactByPhone,
    getContactByEmail,
    contactsWithEmail,
    contactsWithPhone,
    allContacts,
    isLoading,
    isAvailable: !isLoading && contactsState != null,
  };
}
