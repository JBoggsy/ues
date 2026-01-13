---
name: New Modality Request
about: Suggest a new modality to add to UES
title: '[Modality]: '
labels: modality, enhancement
assignees: ''
---

## Modality Name
What modality would you like to see added? (e.g., Contacts, File System, Discord)

## Description
Describe what this modality would simulate and how it would be used.

## Key Operations
What actions should this modality support?

Example:
- `add_contact` - Add a new contact
- `search_contacts` - Search contacts by name/email
- `update_contact` - Update contact information

## State Structure
What data would this modality need to track?

Example:
```python
class ContactState:
    contacts: list[Contact]
    groups: list[ContactGroup]
    favorites: list[str]  # contact IDs
```

## Integration Points
How would this modality interact with existing modalities?

Example:
- Email: Auto-complete addresses from contacts
- Calendar: Show contact names on event invites
- SMS: Link conversations to contacts

## Priority
How important is this modality for your use case?
- [ ] Critical - I can't use UES effectively without it
- [ ] High - Would significantly improve my workflow
- [ ] Medium - Nice to have
- [ ] Low - Just an idea for the future

## Additional Context
Add any other context, examples, or references here.
