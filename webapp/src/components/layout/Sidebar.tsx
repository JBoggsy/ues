/**
 * Sidebar navigation for modalities.
 */
import { NavLink } from 'react-router-dom';
import { 
  Mail, 
  MessageSquare, 
  Calendar, 
  MessageCircle, 
  MapPin, 
  Cloud, 
  Clock,
  LayoutDashboard,
  ListTodo,
  Settings,
  BookUser,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useEnvironmentState } from '@/api';

interface NavItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  modality?: string;
}

const mainNavItems: NavItem[] = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Events', path: '/events', icon: ListTodo },
  { name: 'Settings', path: '/settings', icon: Settings },
];

const modalityNavItems: NavItem[] = [
  { name: 'Email', path: '/modalities/email', icon: Mail, modality: 'email' },
  { name: 'SMS', path: '/modalities/sms', icon: MessageSquare, modality: 'sms' },
  { name: 'Chat', path: '/modalities/chat', icon: MessageCircle, modality: 'chat' },
  { name: 'Calendar', path: '/modalities/calendar', icon: Calendar, modality: 'calendar' },
  { name: 'Contacts', path: '/modalities/contacts', icon: BookUser, modality: 'contacts' },
  { name: 'Location', path: '/modalities/location', icon: MapPin, modality: 'location' },
  { name: 'Weather', path: '/modalities/weather', icon: Cloud, modality: 'weather' },
  { name: 'Time', path: '/modalities/time', icon: Clock, modality: 'time' },
];

export function Sidebar() {
  const { data: environment } = useEnvironmentState();

  const getModalitySummary = (modality: string): string | undefined => {
    if (!environment?.summary) return undefined;
    const found = environment.summary.find(s => s.modality_type === modality);
    return found?.state_summary;
  };

  return (
    <aside className="w-56 border-r bg-muted/30">
      <ScrollArea className="h-full">
        <nav className="p-3 space-y-1">
          {/* Main Navigation */}
          {mainNavItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-muted'
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.name}
            </NavLink>
          ))}

          <Separator className="my-3" />

          {/* Modalities */}
          <p className="px-3 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Modalities
          </p>
          {modalityNavItems.map((item) => {
            const summary = item.modality ? getModalitySummary(item.modality) : undefined;
            
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-muted'
                  )
                }
              >
                <div className="flex items-center gap-3">
                  <item.icon className="h-4 w-4" />
                  {item.name}
                </div>
                {summary && (
                  <Badge variant="secondary" className="text-xs">
                    {summary}
                  </Badge>
                )}
              </NavLink>
            );
          })}
        </nav>
      </ScrollArea>
    </aside>
  );
}
