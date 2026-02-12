/**
 * Main Contacts viewer component.
 * Integrates contact list, detail view, toolbar, and status bar.
 */
import { useState, useCallback, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import apiClient from '@/api/client';
import { useModalityState } from '@/api';
import { ContactList } from './ContactList';
import { ContactDetail } from './ContactDetail';
import { ContactsToolbar } from './ContactsToolbar';
import { ContactsStatusBar } from './ContactsStatusBar';
import { CreateContactDialog } from './CreateContactDialog';
import type { ContactsState, ContactFilter } from './types';

/**
 * Map of contacts operations to their API endpoints.
 */
const CONTACTS_API_ENDPOINTS: Record<string, string> = {
  create: '/contacts/create',
  update: '/contacts/update',
  delete: '/contacts/delete',
  block: '/contacts/block',
  unblock: '/contacts/unblock',
  favorite: '/contacts/favorite',
  unfavorite: '/contacts/unfavorite',
  group_add: '/contacts/group/add',
  group_remove: '/contacts/group/remove',
  merge: '/contacts/merge',
};

/**
 * Submit a contacts action to the API.
 */
async function submitContactsAction(
  endpoint: string,
  data: Record<string, unknown>
): Promise<void> {
  await apiClient.post(endpoint, data);
}

export function ContactsViewer() {
  const queryClient = useQueryClient();

  // Fetch contacts state with polling
  const {
    data: contactsState,
    isLoading,
    isError,
    refetch,
    isRefetching,
  } = useModalityState<ContactsState>('contacts', 3000);

  // UI State
  const [filter, setFilter] = useState<ContactFilter>('all');
  const [selectedContactId, setSelectedContactId] = useState<string | null>(
    null
  );
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // Get selected contact
  const selectedContact = useMemo(() => {
    if (!contactsState || !selectedContactId) return null;
    return contactsState.contacts[selectedContactId] || null;
  }, [contactsState, selectedContactId]);

  // Invalidate queries after mutations
  const invalidateContactsState = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: ['environment', 'modalities', 'contacts'],
    });
  }, [queryClient]);

  // Refresh handler
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Contact selection
  const handleContactSelect = useCallback((contactId: string) => {
    setSelectedContactId(contactId);
  }, []);

  // Create contact
  const handleCreateContact = useCallback(() => {
    setCreateDialogOpen(true);
  }, []);

  // Submit new contact to API
  const handleCreateContactSubmit = useCallback(
    async (data: Record<string, unknown>) => {
      try {
        await submitContactsAction(CONTACTS_API_ENDPOINTS.create, data);
        toast.success('Contact created');
        invalidateContactsState();
      } catch (error) {
        console.error('Failed to create contact:', error);
        toast.error('Failed to create contact');
      }
    },
    [invalidateContactsState]
  );

  // Delete contact
  const handleDelete = useCallback(async () => {
    if (!selectedContactId) return;

    try {
      await submitContactsAction(CONTACTS_API_ENDPOINTS.delete, {
        contact_id: selectedContactId,
      });

      toast.success('Contact deleted');
      setSelectedContactId(null);
      invalidateContactsState();
    } catch (error) {
      console.error('Failed to delete contact:', error);
      toast.error('Failed to delete contact');
    }
  }, [selectedContactId, invalidateContactsState]);

  // Favorite contact
  const handleFavorite = useCallback(async () => {
    if (!selectedContactId) return;

    try {
      await submitContactsAction(CONTACTS_API_ENDPOINTS.favorite, {
        contact_id: selectedContactId,
      });

      toast.success('Contact added to favorites');
      invalidateContactsState();
    } catch (error) {
      console.error('Failed to favorite contact:', error);
      toast.error('Failed to favorite contact');
    }
  }, [selectedContactId, invalidateContactsState]);

  // Unfavorite contact
  const handleUnfavorite = useCallback(async () => {
    if (!selectedContactId) return;

    try {
      await submitContactsAction(CONTACTS_API_ENDPOINTS.unfavorite, {
        contact_id: selectedContactId,
      });

      toast.success('Contact removed from favorites');
      invalidateContactsState();
    } catch (error) {
      console.error('Failed to unfavorite contact:', error);
      toast.error('Failed to unfavorite contact');
    }
  }, [selectedContactId, invalidateContactsState]);

  // Block contact
  const handleBlock = useCallback(async () => {
    if (!selectedContactId) return;

    try {
      await submitContactsAction(CONTACTS_API_ENDPOINTS.block, {
        contact_id: selectedContactId,
      });

      toast.success('Contact blocked');
      invalidateContactsState();
    } catch (error) {
      console.error('Failed to block contact:', error);
      toast.error('Failed to block contact');
    }
  }, [selectedContactId, invalidateContactsState]);

  // Unblock contact
  const handleUnblock = useCallback(async () => {
    if (!selectedContactId) return;

    try {
      await submitContactsAction(CONTACTS_API_ENDPOINTS.unblock, {
        contact_id: selectedContactId,
      });

      toast.success('Contact unblocked');
      invalidateContactsState();
    } catch (error) {
      console.error('Failed to unblock contact:', error);
      toast.error('Failed to unblock contact');
    }
  }, [selectedContactId, invalidateContactsState]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-muted-foreground">Loading contacts...</div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <p className="text-destructive mb-2">Failed to load contacts</p>
          <button
            onClick={() => refetch()}
            className="text-sm text-primary hover:underline"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] border rounded-lg overflow-hidden">
      {/* Toolbar */}
      <ContactsToolbar
        selectedContact={selectedContact}
        onCreateContact={handleCreateContact}
        onDelete={handleDelete}
        onFavorite={handleFavorite}
        onUnfavorite={handleUnfavorite}
        onBlock={handleBlock}
        onUnblock={handleUnblock}
        onRefresh={handleRefresh}
        isRefreshing={isRefetching}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 min-h-0">
        {/* Contact List */}
        <ContactList
          contactsState={contactsState || null}
          selectedContactId={selectedContactId}
          filter={filter}
          onFilterChange={setFilter}
          onContactSelect={handleContactSelect}
        />

        {/* Contact Detail */}
        <ContactDetail contact={selectedContact} />
      </div>

      {/* Status Bar */}
      <ContactsStatusBar contactsState={contactsState || null} />

      {/* Create Contact Dialog */}
      <CreateContactDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSubmit={handleCreateContactSubmit}
      />
    </div>
  );
}
