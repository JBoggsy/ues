/**
 * Event manager page for viewing and managing scheduled events.
 */
import { useState } from 'react';
import { format } from 'date-fns';
import { Trash2, Eye, List, Clock } from 'lucide-react';
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Tabs, 
  TabsContent, 
  TabsList, 
  TabsTrigger 
} from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  ToggleGroup,
  ToggleGroupItem,
} from '@/components/ui/toggle-group';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useEvents, useCancelEvent, useTimeState, type SimulatorEvent, type EventStatus } from '@/api';
import { EventCreationDialog, EventTimeline } from '@/components/events';

const statusColors: Record<EventStatus, string> = {
  pending: 'bg-yellow-500',
  executing: 'bg-blue-500',
  executed: 'bg-green-500',
  failed: 'bg-red-500',
  skipped: 'bg-orange-500',
  cancelled: 'bg-gray-500',
};

function EventCard({ event }: { event: SimulatorEvent }) {
  const cancelEvent = useCancelEvent();
  const [showDetails, setShowDetails] = useState(false);

  const handleCancel = () => {
    if (window.confirm('Cancel this event?')) {
      cancelEvent.mutate(event.event_id);
    }
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${statusColors[event.status]}`} />
            <div>
              <p className="font-medium capitalize">{event.modality}</p>
              <p className="text-sm text-muted-foreground">
                {format(new Date(event.scheduled_time), 'yyyy-MM-dd HH:mm:ss')}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{event.status}</Badge>
            <Dialog open={showDetails} onOpenChange={setShowDetails}>
              <DialogTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Eye className="h-4 w-4" />
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Event Details</DialogTitle>
                </DialogHeader>
                <ScrollArea className="max-h-96">
                  <pre className="text-sm bg-muted p-4 rounded-md overflow-auto">
                    {JSON.stringify(event, null, 2)}
                  </pre>
                </ScrollArea>
              </DialogContent>
            </Dialog>
            {event.status === 'pending' && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleCancel}
                disabled={cancelEvent.isPending}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function EventManager() {
  const [statusFilter, setStatusFilter] = useState<EventStatus | 'all'>('all');
  const [viewMode, setViewMode] = useState<'list' | 'timeline'>('list');
  const [selectedTimelineEvent, setSelectedTimelineEvent] = useState<SimulatorEvent | null>(null);
  
  const { data: eventsData, isLoading } = useEvents(
    statusFilter === 'all' ? undefined : { status: statusFilter }
  );
  const { data: timeData } = useTimeState();

  const events = eventsData?.events || [];
  const currentTime = timeData?.current_time;

  // For timeline view, we want all events regardless of filter
  const { data: allEventsData } = useEvents();
  const allEvents = allEventsData?.events || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Event Manager</h2>
          <p className="text-muted-foreground">
            View and manage scheduled simulation events
          </p>
        </div>
        <div className="flex items-center gap-4">
          <ToggleGroup 
            type="single" 
            value={viewMode} 
            onValueChange={(value) => value && setViewMode(value as 'list' | 'timeline')}
          >
            <ToggleGroupItem value="list" aria-label="List view">
              <List className="h-4 w-4 mr-2" />
              List
            </ToggleGroupItem>
            <ToggleGroupItem value="timeline" aria-label="Timeline view">
              <Clock className="h-4 w-4 mr-2" />
              Timeline
            </ToggleGroupItem>
          </ToggleGroup>
          <EventCreationDialog />
        </div>
      </div>

      {viewMode === 'list' ? (
        // List View
        <Tabs value={statusFilter} onValueChange={(v) => setStatusFilter(v as EventStatus | 'all')}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="executed">Executed</TabsTrigger>
            <TabsTrigger value="failed">Failed</TabsTrigger>
            <TabsTrigger value="skipped">Skipped</TabsTrigger>
            <TabsTrigger value="cancelled">Cancelled</TabsTrigger>
          </TabsList>

          <TabsContent value={statusFilter} className="mt-4">
            {isLoading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <Card key={i} className="animate-pulse">
                    <CardContent className="p-4">
                      <div className="h-12 bg-muted rounded" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : events.length === 0 ? (
              <Card>
                <CardHeader>
                  <CardTitle className="text-center text-muted-foreground">
                    No events found
                  </CardTitle>
                </CardHeader>
              </Card>
            ) : (
              <div className="space-y-2">
                {events.map((event) => (
                  <EventCard key={event.event_id} event={event} />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      ) : (
        // Timeline View
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Timeline View</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[600px]">
                  <EventTimeline
                    events={allEvents}
                    currentTime={currentTime}
                    onEventClick={setSelectedTimelineEvent}
                  />
                </div>
              </CardContent>
            </Card>
          </div>
          
          <div className="lg:col-span-1">
            <Card className="sticky top-4">
              <CardHeader>
                <CardTitle>Event Details</CardTitle>
              </CardHeader>
              <CardContent>
                {selectedTimelineEvent ? (
                  <div className="space-y-4">
                    <div>
                      <span className="text-sm text-muted-foreground">Event ID</span>
                      <p className="font-mono text-sm">{selectedTimelineEvent.event_id}</p>
                    </div>
                    <div>
                      <span className="text-sm text-muted-foreground">Modality</span>
                      <p className="capitalize">{selectedTimelineEvent.modality}</p>
                    </div>
                    <div>
                      <span className="text-sm text-muted-foreground">Status</span>
                      <div className="flex items-center gap-2 mt-1">
                        <div className={`w-2 h-2 rounded-full ${statusColors[selectedTimelineEvent.status]}`} />
                        <span className="capitalize">{selectedTimelineEvent.status}</span>
                      </div>
                    </div>
                    <div>
                      <span className="text-sm text-muted-foreground">Scheduled Time</span>
                      <p>{format(new Date(selectedTimelineEvent.scheduled_time), 'yyyy-MM-dd HH:mm:ss')}</p>
                    </div>
                    <div>
                      <span className="text-sm text-muted-foreground">Data</span>
                      <ScrollArea className="h-48 mt-1">
                        <pre className="text-xs bg-muted p-3 rounded overflow-auto">
                          {JSON.stringify(selectedTimelineEvent.data, null, 2)}
                        </pre>
                      </ScrollArea>
                    </div>
                    <Button 
                      variant="outline" 
                      className="w-full"
                      onClick={() => setSelectedTimelineEvent(null)}
                    >
                      Clear Selection
                    </Button>
                  </div>
                ) : (
                  <p className="text-muted-foreground text-center py-8">
                    Click an event on the timeline to view details
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
