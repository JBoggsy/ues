/**
 * Time scale slider control.
 */
import { Slider } from '@/components/ui/slider';
import { Button } from '@/components/ui/button';
import { useTimeState, useSetTimeScale } from '@/api';

const SCALE_PRESETS = [0.5, 1, 2, 5, 10];

export function TimeScaleSlider() {
  const { data: timeState } = useTimeState();
  const setTimeScale = useSetTimeScale();

  const currentScale = timeState?.time_scale ?? 1;

  const handleSliderChange = (value: number[]) => {
    setTimeScale.mutate({ scale: value[0] });
  };

  const handlePresetClick = (scale: number) => {
    setTimeScale.mutate({ scale: scale });
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Time Scale</span>
        <span className="text-sm text-muted-foreground">{currentScale}x</span>
      </div>
      
      <Slider
        value={[currentScale]}
        onValueChange={handleSliderChange}
        min={0.1}
        max={10}
        step={0.1}
        className="w-full"
      />
      
      <div className="flex gap-1">
        {SCALE_PRESETS.map((scale) => (
          <Button
            key={scale}
            variant={currentScale === scale ? 'default' : 'outline'}
            size="sm"
            onClick={() => handlePresetClick(scale)}
            className="flex-1"
          >
            {scale}x
          </Button>
        ))}
      </div>
    </div>
  );
}
