/**
 * Settings history component showing past time preference changes.
 * Each entry is collapsed by default but can be expanded to show details.
 */
import { useState, useCallback, useMemo } from 'react';
import { History, ChevronDown, ChevronRight, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { TimeSettingsHistoryEntry } from './types';

interface SettingsHistoryProps {
  history: TimeSettingsHistoryEntry[];
  currentSettings: {
    timezone: string;
    format_preference: string;
    date_format: string | null;
    locale: string | null;
    week_start: string | null;
  };
}

interface HistoryEntryProps {
  entry: TimeSettingsHistoryEntry;
  previousEntry?: TimeSettingsHistoryEntry;
  isExpanded: boolean;
  onToggle: () => void;
}

/**
 * Format a timestamp for display.
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Detect what changed between two settings entries.
 */
function detectChanges(
  from: TimeSettingsHistoryEntry | undefined,
  to: TimeSettingsHistoryEntry
): { field: string; from: string; to: string }[] {
  const changes: { field: string; from: string; to: string }[] = [];

  if (!from) {
    // Initial settings - show all as "set"
    changes.push({ field: 'Timezone', from: '(initial)', to: to.timezone });
    changes.push({ field: 'Format', from: '(initial)', to: to.format_preference });
    if (to.date_format) {
      changes.push({ field: 'Date Format', from: '(none)', to: to.date_format });
    }
    if (to.locale) {
      changes.push({ field: 'Locale', from: '(none)', to: to.locale });
    }
    if (to.week_start) {
      changes.push({ field: 'Week Start', from: '(none)', to: to.week_start });
    }
    return changes;
  }

  if (from.timezone !== to.timezone) {
    changes.push({ field: 'Timezone', from: from.timezone, to: to.timezone });
  }
  if (from.format_preference !== to.format_preference) {
    changes.push({
      field: 'Format',
      from: from.format_preference,
      to: to.format_preference,
    });
  }
  if (from.date_format !== to.date_format) {
    changes.push({
      field: 'Date Format',
      from: from.date_format || '(none)',
      to: to.date_format || '(none)',
    });
  }
  if (from.locale !== to.locale) {
    changes.push({
      field: 'Locale',
      from: from.locale || '(none)',
      to: to.locale || '(none)',
    });
  }
  if (from.week_start !== to.week_start) {
    changes.push({
      field: 'Week Start',
      from: from.week_start || '(none)',
      to: to.week_start || '(none)',
    });
  }

  return changes;
}

/**
 * Single history entry row.
 */
function HistoryEntry({
  entry,
  previousEntry,
  isExpanded,
  onToggle,
}: HistoryEntryProps) {
  const changes = useMemo(
    () => detectChanges(previousEntry, entry),
    [entry, previousEntry]
  );

  // Generate a brief summary of changes
  const changeSummary = useMemo(() => {
    if (changes.length === 0) return 'No changes detected';
    if (changes.length === 1) return `Changed ${changes[0].field.toLowerCase()}`;
    return `Changed ${changes.length} settings`;
  }, [changes]);

  return (
    <div className="border rounded-lg overflow-hidden">
      <Button
        variant="ghost"
        className="w-full justify-start gap-2 px-3 py-2 h-auto font-normal hover:bg-muted/50"
        onClick={onToggle}
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0" />
        )}
        <span className="text-xs text-muted-foreground shrink-0">
          {formatTimestamp(entry.timestamp)}
        </span>
        <span className="text-sm truncate">{changeSummary}</span>
      </Button>

      {isExpanded && changes.length > 0 && (
        <div className="px-3 pb-3 pt-1 space-y-1 bg-muted/20">
          {changes.map((change, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 text-xs"
            >
              <span className="text-muted-foreground w-20 shrink-0">
                {change.field}:
              </span>
              <span className="text-muted-foreground truncate max-w-[80px]" title={change.from}>
                {change.from}
              </span>
              <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground" />
              <span className="font-medium truncate max-w-[80px]" title={change.to}>
                {change.to}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function SettingsHistory({ history }: SettingsHistoryProps) {
  // Track which entries are expanded (by index)
  const [expandedIndices, setExpandedIndices] = useState<Set<number>>(new Set());

  const toggleExpanded = useCallback((index: number) => {
    setExpandedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  // Reverse history so most recent is first
  const reversedHistory = useMemo(
    () => [...history].reverse(),
    [history]
  );

  // Also reverse for previous entry lookup
  const getPreviousEntry = useCallback(
    (reversedIndex: number): TimeSettingsHistoryEntry | undefined => {
      // In reversed array, "previous" means next in the original array
      // which is reversedIndex + 1 in the reversed array
      const prevReversedIndex = reversedIndex + 1;
      return reversedHistory[prevReversedIndex];
    },
    [reversedHistory]
  );

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium flex items-center justify-between">
          <span className="flex items-center gap-2">
            <History className="h-4 w-4" />
            Settings History
          </span>
          <span className="text-xs font-normal text-muted-foreground">
            {history.length} {history.length === 1 ? 'entry' : 'entries'}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {reversedHistory.length === 0 ? (
          <div className="text-center py-6 text-muted-foreground text-sm">
            No history yet. Changes will appear here after you modify settings.
          </div>
        ) : (
          <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
            {reversedHistory.map((entry, idx) => (
              <HistoryEntry
                key={`${entry.timestamp}-${idx}`}
                entry={entry}
                previousEntry={getPreviousEntry(idx)}
                isExpanded={expandedIndices.has(idx)}
                onToggle={() => toggleExpanded(idx)}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
