/**
 * Create contact dialog for the Contacts viewer.
 * Modal form for creating a new contact with identifiers, addresses,
 * and other metadata.
 */
import { useState, useCallback } from 'react';
import {
  Plus,
  Trash2,
  UserPlus,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

/**
 * Form data for an identifier entry.
 */
interface IdentifierFormEntry {
  identifier_type: string;
  value: string;
  label: string;
}

/**
 * Form data for an address entry.
 */
interface AddressFormEntry {
  street: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  label: string;
}

/**
 * Complete form data for creating a contact.
 */
interface CreateContactFormData {
  first_name: string;
  last_name: string;
  display_name: string;
  nickname: string;
  company: string;
  job_title: string;
  birthday: string;
  notes: string;
  photo_url: string;
  is_favorite: boolean;
  identifiers: IdentifierFormEntry[];
  addresses: AddressFormEntry[];
  groups: string;
}

function emptyIdentifier(): IdentifierFormEntry {
  return { identifier_type: 'phone', value: '', label: '' };
}

function emptyAddress(): AddressFormEntry {
  return {
    street: '',
    city: '',
    state: '',
    postal_code: '',
    country: '',
    label: '',
  };
}

function emptyFormData(): CreateContactFormData {
  return {
    first_name: '',
    last_name: '',
    display_name: '',
    nickname: '',
    company: '',
    job_title: '',
    birthday: '',
    notes: '',
    photo_url: '',
    is_favorite: false,
    identifiers: [emptyIdentifier()],
    addresses: [],
    groups: '',
  };
}

interface CreateContactDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: Record<string, unknown>) => void;
}

export function CreateContactDialog({
  open,
  onOpenChange,
  onSubmit,
}: CreateContactDialogProps) {
  const [form, setForm] = useState<CreateContactFormData>(emptyFormData());
  const [showOptional, setShowOptional] = useState(false);

  // Reset form when dialog opens
  const handleOpenChange = useCallback(
    (isOpen: boolean) => {
      if (isOpen) {
        setForm(emptyFormData());
        setShowOptional(false);
      }
      onOpenChange(isOpen);
    },
    [onOpenChange]
  );

  // Update a scalar field
  const updateField = useCallback(
    (field: keyof CreateContactFormData, value: string | boolean) => {
      setForm((prev) => ({ ...prev, [field]: value }));
    },
    []
  );

  // Identifier management
  const addIdentifier = useCallback(() => {
    setForm((prev) => ({
      ...prev,
      identifiers: [...prev.identifiers, emptyIdentifier()],
    }));
  }, []);

  const removeIdentifier = useCallback((index: number) => {
    setForm((prev) => ({
      ...prev,
      identifiers: prev.identifiers.filter((_, i) => i !== index),
    }));
  }, []);

  const updateIdentifier = useCallback(
    (index: number, field: keyof IdentifierFormEntry, value: string) => {
      setForm((prev) => ({
        ...prev,
        identifiers: prev.identifiers.map((entry, i) =>
          i === index ? { ...entry, [field]: value } : entry
        ),
      }));
    },
    []
  );

  // Address management
  const addAddress = useCallback(() => {
    setForm((prev) => ({
      ...prev,
      addresses: [...prev.addresses, emptyAddress()],
    }));
  }, []);

  const removeAddress = useCallback((index: number) => {
    setForm((prev) => ({
      ...prev,
      addresses: prev.addresses.filter((_, i) => i !== index),
    }));
  }, []);

  const updateAddress = useCallback(
    (index: number, field: keyof AddressFormEntry, value: string) => {
      setForm((prev) => ({
        ...prev,
        addresses: prev.addresses.map((entry, i) =>
          i === index ? { ...entry, [field]: value } : entry
        ),
      }));
    },
    []
  );

  // Validate: at least one identifier with a non-empty value
  const isValid =
    form.identifiers.length > 0 &&
    form.identifiers.some((id) => id.value.trim().length > 0);

  // Build API payload and submit
  const handleSubmit = useCallback(() => {
    if (!isValid) return;

    // Build identifiers array (filter out empty ones)
    const identifiers = form.identifiers
      .filter((id) => id.value.trim())
      .map((id) => ({
        identifier_type: id.identifier_type,
        value: id.value.trim(),
        ...(id.label.trim() ? { label: id.label.trim() } : {}),
      }));

    // Build addresses array (filter out fully-empty ones)
    const addresses = form.addresses
      .filter(
        (addr) =>
          addr.street.trim() ||
          addr.city.trim() ||
          addr.state.trim() ||
          addr.postal_code.trim() ||
          addr.country.trim()
      )
      .map((addr) => {
        const a: Record<string, string> = {};
        if (addr.street.trim()) a.street = addr.street.trim();
        if (addr.city.trim()) a.city = addr.city.trim();
        if (addr.state.trim()) a.state = addr.state.trim();
        if (addr.postal_code.trim()) a.postal_code = addr.postal_code.trim();
        if (addr.country.trim()) a.country = addr.country.trim();
        if (addr.label.trim()) a.label = addr.label.trim();
        return a;
      });

    // Build groups array from comma-separated string
    const groups = form.groups
      .split(',')
      .map((g) => g.trim())
      .filter((g) => g.length > 0);

    const payload: Record<string, unknown> = { identifiers };

    if (form.first_name.trim()) payload.first_name = form.first_name.trim();
    if (form.last_name.trim()) payload.last_name = form.last_name.trim();
    if (form.display_name.trim())
      payload.display_name = form.display_name.trim();
    if (form.nickname.trim()) payload.nickname = form.nickname.trim();
    if (form.company.trim()) payload.company = form.company.trim();
    if (form.job_title.trim()) payload.job_title = form.job_title.trim();
    if (form.birthday.trim()) payload.birthday = form.birthday.trim();
    if (form.notes.trim()) payload.notes = form.notes.trim();
    if (form.photo_url.trim()) payload.photo_url = form.photo_url.trim();
    if (form.is_favorite) payload.is_favorite = true;
    if (addresses.length > 0) payload.addresses = addresses;
    if (groups.length > 0) payload.groups = groups;

    onSubmit(payload);
    handleOpenChange(false);
  }, [form, isValid, onSubmit, handleOpenChange]);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="h-5 w-5" />
            Create Contact
          </DialogTitle>
          <DialogDescription>
            Add a new contact. At least one identifier (phone, email, etc.) is
            required.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Name fields */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="first_name">First Name</Label>
              <Input
                id="first_name"
                placeholder="Jane"
                value={form.first_name}
                onChange={(e) => updateField('first_name', e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="last_name">Last Name</Label>
              <Input
                id="last_name"
                placeholder="Doe"
                value={form.last_name}
                onChange={(e) => updateField('last_name', e.target.value)}
              />
            </div>
          </div>

          <Separator />

          {/* Identifiers */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label>Identifiers *</Label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={addIdentifier}
              >
                <Plus className="h-3 w-3 mr-1" />
                Add
              </Button>
            </div>
            <div className="space-y-2">
              {form.identifiers.map((identifier, idx) => (
                <div key={idx} className="flex items-end gap-2">
                  <div className="w-28">
                    <Select
                      value={identifier.identifier_type}
                      onValueChange={(v) =>
                        updateIdentifier(idx, 'identifier_type', v)
                      }
                    >
                      <SelectTrigger className="h-9 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="phone">Phone</SelectItem>
                        <SelectItem value="email">Email</SelectItem>
                        <SelectItem value="discord">Discord</SelectItem>
                        <SelectItem value="twitter">Twitter</SelectItem>
                        <SelectItem value="github">GitHub</SelectItem>
                        <SelectItem value="linkedin">LinkedIn</SelectItem>
                        <SelectItem value="slack">Slack</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex-1">
                    <Input
                      placeholder={
                        identifier.identifier_type === 'phone'
                          ? '+1-555-0100'
                          : identifier.identifier_type === 'email'
                            ? 'jane@example.com'
                            : 'handle or value'
                      }
                      value={identifier.value}
                      onChange={(e) =>
                        updateIdentifier(idx, 'value', e.target.value)
                      }
                      className="h-9"
                    />
                  </div>
                  <div className="w-20">
                    <Input
                      placeholder="Label"
                      value={identifier.label}
                      onChange={(e) =>
                        updateIdentifier(idx, 'label', e.target.value)
                      }
                      className="h-9 text-xs"
                    />
                  </div>
                  {form.identifiers.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-9 w-9 flex-shrink-0"
                      onClick={() => removeIdentifier(idx)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Toggle for optional fields */}
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-full text-xs"
            onClick={() => setShowOptional(!showOptional)}
          >
            {showOptional ? 'Hide' : 'Show'} optional fields
          </Button>

          {showOptional && (
            <>
              <Separator />

              {/* Display name & Nickname */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="display_name">Display Name</Label>
                  <Input
                    id="display_name"
                    placeholder="e.g. Mom, Dr. Smith"
                    value={form.display_name}
                    onChange={(e) =>
                      updateField('display_name', e.target.value)
                    }
                  />
                </div>
                <div>
                  <Label htmlFor="nickname">Nickname</Label>
                  <Input
                    id="nickname"
                    placeholder="Nickname"
                    value={form.nickname}
                    onChange={(e) => updateField('nickname', e.target.value)}
                  />
                </div>
              </div>

              {/* Work */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="company">Company</Label>
                  <Input
                    id="company"
                    placeholder="Acme Corp"
                    value={form.company}
                    onChange={(e) => updateField('company', e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="job_title">Job Title</Label>
                  <Input
                    id="job_title"
                    placeholder="Software Engineer"
                    value={form.job_title}
                    onChange={(e) => updateField('job_title', e.target.value)}
                  />
                </div>
              </div>

              {/* Addresses */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label>Addresses</Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={addAddress}
                  >
                    <Plus className="h-3 w-3 mr-1" />
                    Add
                  </Button>
                </div>
                {form.addresses.map((address, idx) => (
                  <div
                    key={idx}
                    className="border rounded-md p-3 mb-2 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">
                        Address {idx + 1}
                      </span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => removeAddress(idx)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                    <Input
                      placeholder="Street"
                      value={address.street}
                      onChange={(e) =>
                        updateAddress(idx, 'street', e.target.value)
                      }
                      className="h-8 text-sm"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        placeholder="City"
                        value={address.city}
                        onChange={(e) =>
                          updateAddress(idx, 'city', e.target.value)
                        }
                        className="h-8 text-sm"
                      />
                      <Input
                        placeholder="State"
                        value={address.state}
                        onChange={(e) =>
                          updateAddress(idx, 'state', e.target.value)
                        }
                        className="h-8 text-sm"
                      />
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <Input
                        placeholder="ZIP"
                        value={address.postal_code}
                        onChange={(e) =>
                          updateAddress(idx, 'postal_code', e.target.value)
                        }
                        className="h-8 text-sm"
                      />
                      <Input
                        placeholder="Country"
                        value={address.country}
                        onChange={(e) =>
                          updateAddress(idx, 'country', e.target.value)
                        }
                        className="h-8 text-sm"
                      />
                      <Input
                        placeholder="Label"
                        value={address.label}
                        onChange={(e) =>
                          updateAddress(idx, 'label', e.target.value)
                        }
                        className="h-8 text-sm"
                      />
                    </div>
                  </div>
                ))}
                {form.addresses.length === 0 && (
                  <p className="text-xs text-muted-foreground">
                    No addresses added.
                  </p>
                )}
              </div>

              {/* Birthday, Groups, Photo URL */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="birthday">Birthday</Label>
                  <Input
                    id="birthday"
                    type="date"
                    value={form.birthday}
                    onChange={(e) => updateField('birthday', e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="groups">Groups</Label>
                  <Input
                    id="groups"
                    placeholder="Family, Work, ..."
                    value={form.groups}
                    onChange={(e) => updateField('groups', e.target.value)}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="photo_url">Photo URL</Label>
                <Input
                  id="photo_url"
                  placeholder="https://..."
                  value={form.photo_url}
                  onChange={(e) => updateField('photo_url', e.target.value)}
                />
              </div>

              {/* Notes */}
              <div>
                <Label htmlFor="notes">Notes</Label>
                <Textarea
                  id="notes"
                  placeholder="Additional notes..."
                  value={form.notes}
                  onChange={(e) => updateField('notes', e.target.value)}
                  rows={2}
                />
              </div>

              {/* Favorite checkbox */}
              <div className="flex items-center gap-2">
                <Checkbox
                  id="is_favorite"
                  checked={form.is_favorite}
                  onCheckedChange={(checked) =>
                    updateField('is_favorite', !!checked)
                  }
                />
                <Label htmlFor="is_favorite" className="text-sm font-normal">
                  Add to favorites
                </Label>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!isValid}>
            <UserPlus className="h-4 w-4 mr-2" />
            Create Contact
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
