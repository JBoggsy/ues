/**
 * Main dashboard page showing simulation overview and modality summaries.
 */
import { 
  Mail, 
  MessageSquare, 
  Calendar, 
  MessageCircle, 
  MapPin, 
  Cloud, 
  Clock 
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  SimulationStatus, 
  TimeScaleSlider, 
  TimeAdvanceControls 
} from '@/components/simulation';
import { useEnvironmentState, useEventSummary } from '@/api';

const modalityIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  email: Mail,
  sms: MessageSquare,
  chat: MessageCircle,
  calendar: Calendar,
  location: MapPin,
  weather: Cloud,
  time: Clock,
};

export function Dashboard() {
  const { data: environment, isLoading: envLoading } = useEnvironmentState();
  const { data: eventSummary } = useEventSummary();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Overview of your simulation environment
        </p>
      </div>

      {/* Simulation Controls Row */}
      <div className="grid gap-4 md:grid-cols-3">
        <SimulationStatus />
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Time Scale</CardTitle>
          </CardHeader>
          <CardContent>
            <TimeScaleSlider />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Time Control</CardTitle>
          </CardHeader>
          <CardContent>
            <TimeAdvanceControls />
          </CardContent>
        </Card>
      </div>

      {/* Event Summary */}
      {eventSummary && (
        <Card>
          <CardHeader>
            <CardTitle>Event Queue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-6 text-sm">
              <div>
                <span className="text-muted-foreground">Total: </span>
                <span className="font-medium">{eventSummary.total}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Pending: </span>
                <span className="font-medium">{eventSummary.pending}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Executed: </span>
                <span className="font-medium">{eventSummary.executed}</span>
              </div>
              {eventSummary.next_event_time && (
                <div>
                  <span className="text-muted-foreground">Next Event: </span>
                  <span className="font-medium">
                    {new Date(eventSummary.next_event_time).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Modality Cards */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Modalities</h3>
        {envLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[...Array(7)].map((_, i) => (
              <Card key={i} className="animate-pulse">
                <CardContent className="p-6">
                  <div className="h-16 bg-muted rounded" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {(environment?.summary || []).map((item) => {
              const modality = item.modality_type;
              const Icon = modalityIcons[modality] || Clock;
              return (
                <Link key={modality} to={`/modalities/${modality}`}>
                  <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
                    <CardContent className="p-6">
                      <div className="flex items-center gap-3">
                        <Icon className="h-8 w-8 text-muted-foreground" />
                        <div>
                          <p className="font-medium capitalize">{modality}</p>
                          <p className="text-sm text-muted-foreground">
                            {item.state_summary || 'No data'}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
