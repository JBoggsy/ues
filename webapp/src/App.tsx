/**
 * Main application component with routing configuration.
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from '@/components/layout';
import { Dashboard, EventManager, ModalityPage, Settings } from '@/pages';
import { TimelineDemo } from '@/pages/TimelineDemo';
import { Toaster } from '@/components/ui/sonner';
import { ThemeProvider } from '@/lib/theme';
import { useSettingsStore } from '@/lib/store';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000,
      retry: 1,
    },
  },
});

function AppContent() {
  const toastDuration = useSettingsStore((state) => state.toastDuration);
  
  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="events" element={<EventManager />} />
            <Route path="settings" element={<Settings />} />
            <Route path="modalities/:modality" element={<ModalityPage />} />
          </Route>
          {/* Demo pages (outside main layout) */}
          <Route path="/demo/timeline" element={<TimelineDemo />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="bottom-right" duration={toastDuration} />
    </>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AppContent />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
