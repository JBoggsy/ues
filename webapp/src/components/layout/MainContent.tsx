/**
 * Main content area wrapper.
 */
import { ScrollArea } from '@/components/ui/scroll-area';

interface MainContentProps {
  children: React.ReactNode;
}

export function MainContent({ children }: MainContentProps) {
  return (
    <main className="flex-1 overflow-hidden">
      <ScrollArea className="h-full">
        <div className="p-6">
          {children}
        </div>
      </ScrollArea>
    </main>
  );
}
