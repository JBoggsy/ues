/**
 * Component displaying current weather conditions.
 */
import { 
  Wind, 
  Droplets, 
  Gauge, 
  Sun, 
  Eye, 
  Cloud, 
  Sunrise, 
  Sunset 
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { CurrentWeather, UnitSystem } from './types';
import { 
  formatTemperature, 
  formatWindSpeed, 
  windDegToDirection, 
  getWeatherEmoji,
  formatTime 
} from './types';

interface CurrentConditionsProps {
  /** Current weather data */
  current: CurrentWeather;
  /** Timezone offset in seconds */
  timezoneOffset?: number;
  /** Current unit system */
  units: UnitSystem;
}

interface WeatherStatProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

function WeatherStat({ icon, label, value }: WeatherStatProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-muted-foreground">{icon}</span>
      <div>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="text-sm font-medium">{value}</div>
      </div>
    </div>
  );
}

export function CurrentConditions({ current, timezoneOffset, units }: CurrentConditionsProps) {
  const weather = current.weather?.[0];
  
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Current Conditions</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Main temperature display */}
        <div className="flex items-center gap-4 mb-4">
          <span className="text-5xl">
            {weather ? getWeatherEmoji(weather.icon) : '🌡️'}
          </span>
          <div>
            <div className="text-4xl font-bold">
              {formatTemperature(current.temp, units)}
            </div>
            {weather && (
              <div className="text-lg text-muted-foreground capitalize">
                {weather.description}
              </div>
            )}
          </div>
        </div>

        {/* Feels like */}
        <div className="text-sm text-muted-foreground mb-4">
          Feels like: <span className="font-medium">{formatTemperature(current.feels_like, units)}</span>
        </div>

        {/* Weather stats grid */}
        <div className="grid grid-cols-2 gap-4">
          <WeatherStat
            icon={<Wind className="h-4 w-4" />}
            label="Wind"
            value={`${formatWindSpeed(current.wind_speed, units)} ${windDegToDirection(current.wind_deg)}`}
          />
          <WeatherStat
            icon={<Droplets className="h-4 w-4" />}
            label="Humidity"
            value={`${current.humidity}%`}
          />
          <WeatherStat
            icon={<Gauge className="h-4 w-4" />}
            label="Pressure"
            value={`${current.pressure} hPa`}
          />
          <WeatherStat
            icon={<Sun className="h-4 w-4" />}
            label="UV Index"
            value={`${current.uvi}`}
          />
          <WeatherStat
            icon={<Eye className="h-4 w-4" />}
            label="Visibility"
            value={`${(current.visibility / 1000).toFixed(1)} km`}
          />
          <WeatherStat
            icon={<Cloud className="h-4 w-4" />}
            label="Clouds"
            value={`${current.clouds}%`}
          />
          <WeatherStat
            icon={<Sunrise className="h-4 w-4" />}
            label="Sunrise"
            value={formatTime(current.sunrise, timezoneOffset)}
          />
          <WeatherStat
            icon={<Sunset className="h-4 w-4" />}
            label="Sunset"
            value={formatTime(current.sunset, timezoneOffset)}
          />
        </div>
      </CardContent>
    </Card>
  );
}
