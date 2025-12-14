/**
 * Timeline Demo Page
 * 
 * Temporary page to preview the EventTimeline component with sample data.
 * Now featuring: proportional spacing, zoom, date headers, filters, and jump to current.
 */

import { useState } from 'react';
import { EventTimeline } from '@/components/events/EventTimeline';
import { Button } from '@/components/ui/button';
import type { SimulatorEvent } from '@/api/types';

// Sample events spanning multiple days to showcase date headers and gap indicators
const SAMPLE_EVENTS: SimulatorEvent[] = [
  // Day 1: January 14
  {
    event_id: 'evt-0',
    scheduled_time: '2025-01-14T18:00:00Z',
    modality: 'email',
    data: { operation: 'receive', subject: 'Project kickoff tomorrow', from_address: 'manager@example.com' },
    status: 'executed',
  },
  {
    event_id: 'evt-0b',
    scheduled_time: '2025-01-14T22:00:00Z',
    modality: 'location',
    data: { latitude: 40.7128, longitude: -74.0060, named_location: 'Home' },
    status: 'executed',
  },
  
  // Day 2: January 15 - Main day with many events
  {
    event_id: 'evt-1',
    scheduled_time: '2025-01-15T08:00:00Z',
    modality: 'location',
    data: { latitude: 40.7128, longitude: -74.0060, named_location: 'Home' },
    status: 'executed',
  },
  {
    event_id: 'evt-2',
    scheduled_time: '2025-01-15T08:05:00Z', // 5 min later - close together
    modality: 'weather',
    data: { temp_f: 42, condition: 'Cloudy' },
    status: 'executed',
  },
  {
    event_id: 'evt-3',
    scheduled_time: '2025-01-15T09:00:00Z', // 55 min gap
    modality: 'email',
    data: { operation: 'receive', subject: 'Team standup meeting notes', from_address: 'alice@example.com' },
    status: 'executed',
  },
  {
    event_id: 'evt-4',
    scheduled_time: '2025-01-15T09:15:00Z',
    modality: 'chat',
    data: { role: 'user', content: 'What meetings do I have today?' },
    status: 'executed',
  },
  {
    event_id: 'evt-5',
    scheduled_time: '2025-01-15T09:15:30Z', // 30 seconds later - very close
    modality: 'chat',
    data: { role: 'assistant', content: 'You have 3 meetings today: Team standup at 10am, 1:1 with Sarah at 2pm, and Project review at 4pm.' },
    status: 'executed',
  },
  {
    event_id: 'evt-6',
    scheduled_time: '2025-01-15T10:00:00Z',
    modality: 'calendar',
    data: { operation: 'create', title: 'Team Standup' },
    status: 'pending',
  },
  {
    event_id: 'evt-7',
    scheduled_time: '2025-01-15T10:30:00Z',
    modality: 'sms',
    data: { action: 'receive_message', body: 'Running 5 min late to standup', from_number: '+15551234567' },
    status: 'pending',
  },
  {
    event_id: 'evt-8',
    scheduled_time: '2025-01-15T11:00:00Z',
    modality: 'time',
    data: { timezone: 'America/New_York', format_preference: '12h' },
    status: 'pending',
  },
  // 1 hour gap to 12:00
  {
    event_id: 'evt-9',
    scheduled_time: '2025-01-15T12:00:00Z',
    modality: 'location',
    data: { latitude: 40.7580, longitude: -73.9855, named_location: 'Office - Midtown' },
    status: 'pending',
  },
  // 2 hour gap to 14:00
  {
    event_id: 'evt-10',
    scheduled_time: '2025-01-15T14:00:00Z',
    modality: 'email',
    data: { operation: 'send', subject: 'Re: Project timeline update', to_addresses: 'bob@example.com' },
    status: 'cancelled',
  },
  {
    event_id: 'evt-11',
    scheduled_time: '2025-01-15T14:05:00Z',
    modality: 'calendar',
    data: { operation: 'create', title: '1:1 with Sarah' },
    status: 'pending',
  },
  
  // 6 hour gap
  {
    event_id: 'evt-12',
    scheduled_time: '2025-01-15T20:00:00Z',
    modality: 'weather',
    data: { temp_f: 35, condition: 'Clear' },
    status: 'failed',
  },
  
  // Day 3: January 16
  {
    event_id: 'evt-13',
    scheduled_time: '2025-01-16T09:00:00Z',
    modality: 'email',
    data: { operation: 'receive', subject: 'Follow up from yesterday', from_address: 'alice@example.com' },
    status: 'pending',
  },
  {
    event_id: 'evt-14',
    scheduled_time: '2025-01-16T10:00:00Z',
    modality: 'calendar',
    data: { operation: 'create', title: 'Weekly Team Sync' },
    status: 'pending',
  },
];

export function TimelineDemo() {
  const [selectedEvent, setSelectedEvent] = useState<SimulatorEvent | null>(null);
  
  // Simulated current time - between executed and pending events
  const currentTime = '2025-01-15T09:45:00Z';

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Event Timeline Demo</h1>
          <p className="text-muted-foreground">
            Preview of the vertical timeline visualization component
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Timeline */}
          <div className="lg:col-span-2">
            <div className="rounded-lg border bg-card p-6">
              <h2 className="text-xl font-semibold mb-4">Timeline View</h2>
              <div className="h-[600px] overflow-y-auto">
                <EventTimeline 
                  events={SAMPLE_EVENTS}
                  currentTime={currentTime}
                  onEventClick={setSelectedEvent}
                />
              </div>
            </div>
          </div>

          {/* Selected Event Details */}
          <div className="lg:col-span-1">
            <div className="rounded-lg border bg-card p-6 sticky top-8">
              <h2 className="text-xl font-semibold mb-4">Event Details</h2>
              {selectedEvent ? (
                <div className="space-y-4">
                  <div>
                    <span className="text-sm text-muted-foreground">Event ID</span>
                    <p className="font-mono text-sm">{selectedEvent.event_id}</p>
                  </div>
                  <div>
                    <span className="text-sm text-muted-foreground">Modality</span>
                    <p className="capitalize">{selectedEvent.modality}</p>
                  </div>
                  <div>
                    <span className="text-sm text-muted-foreground">Status</span>
                    <p className="capitalize">{selectedEvent.status}</p>
                  </div>
                  <div>
                    <span className="text-sm text-muted-foreground">Scheduled Time</span>
                    <p>{new Date(selectedEvent.scheduled_time).toLocaleString()}</p>
                  </div>
                  <div>
                    <span className="text-sm text-muted-foreground">Data</span>
                    <pre className="mt-1 p-3 bg-muted rounded text-xs overflow-auto max-h-48">
                      {JSON.stringify(selectedEvent.data, null, 2)}
                    </pre>
                  </div>
                  <Button 
                    variant="outline" 
                    className="w-full"
                    onClick={() => setSelectedEvent(null)}
                  >
                    Clear Selection
                  </Button>
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-8">
                  Click an event on the timeline to view details
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Design Notes */}
        <div className="mt-8 rounded-lg border bg-card p-6">
          <h2 className="text-xl font-semibold mb-4">Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 text-sm">
            <div>
              <h3 className="font-medium mb-2">📐 Layout</h3>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Vertical centered timeline</li>
                <li>Alternating left/right cards</li>
                <li>Proportional time-based spacing</li>
                <li>Date headers with horizontal lines</li>
                <li>Gap indicators for long pauses</li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium mb-2">🎨 Visual Design</h3>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Color-coded by modality</li>
                <li>Status indicators on dots</li>
                <li>Diamond marker for current time</li>
                <li>Executed: hollow dot</li>
                <li>Pending: solid dot + ring</li>
                <li>Cancelled/Failed: faded/red</li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium mb-2">🛠️ Interactions</h3>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Ctrl + Mouse Wheel to zoom</li>
                <li>Filter by modality</li>
                <li>Filter by status</li>
                <li>Jump to current time</li>
                <li>Click to select events</li>
                <li>Zoom buttons with percentage</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
