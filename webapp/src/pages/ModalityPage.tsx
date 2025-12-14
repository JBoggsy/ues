/**
 * Generic modality detail page - placeholder for modality-specific viewers.
 */
import { useParams } from 'react-router-dom';
import { 
  Mail, 
  MessageSquare, 
  Calendar, 
  MessageCircle, 
  MapPin, 
  Cloud, 
  Clock 
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useModalityState } from '@/api';

const modalityIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  email: Mail,
  sms: MessageSquare,
  chat: MessageCircle,
  calendar: Calendar,
  location: MapPin,
  weather: Cloud,
  time: Clock,
};

export function ModalityPage() {
  const { modality } = useParams<{ modality: string }>();
  const { data: state, isLoading, isError } = useModalityState(modality as any);

  const Icon = modality ? modalityIcons[modality] || Clock : Clock;

  if (!modality) {
    return (
      <div className="text-center text-muted-foreground">
        Invalid modality
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Icon className="h-8 w-8 text-muted-foreground" />
        <div>
          <h2 className="text-2xl font-bold tracking-tight capitalize">{modality}</h2>
          <p className="text-muted-foreground">
            View and manage {modality} state
          </p>
        </div>
      </div>

      {isLoading ? (
        <Card className="animate-pulse">
          <CardContent className="p-6">
            <div className="h-64 bg-muted rounded" />
          </CardContent>
        </Card>
      ) : isError ? (
        <Card>
          <CardContent className="p-6 text-center text-destructive">
            Failed to load {modality} state
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Current State</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-96">
              <pre className="text-sm bg-muted p-4 rounded-md overflow-auto">
                {JSON.stringify(state, null, 2)}
              </pre>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Placeholder for modality-specific components */}
      <Card>
        <CardHeader>
          <CardTitle>Modality Viewer</CardTitle>
        </CardHeader>
        <CardContent className="text-center text-muted-foreground py-12">
          <p>Detailed {modality} viewer coming soon.</p>
          <p className="text-sm mt-2">
            This will include modality-specific views and actions.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
