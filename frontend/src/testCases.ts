export interface TripFormValues {
  current: string
  pickup: string
  dropoff: string
  cycle: string
  start: string
}

export interface TestCase {
  name: string
  description: string
  values: Omit<TripFormValues, 'start'>
}

export const TEST_CASES: TestCase[] = [
  {
    name: 'Test case 1',
    description: 'Short haul, ~475 mi - fits in one day, no rest needed',
    values: { current: 'Los Angeles, CA', pickup: 'San Diego, CA', dropoff: 'Phoenix, AZ', cycle: '10' },
  },
  {
    name: 'Test case 2',
    description: 'Cross-country, ~2,800 mi at 60 hrs used - fuel stops, 10-hr rests and a 34-hr restart',
    values: { current: 'New York, NY', pickup: 'Chicago, IL', dropoff: 'Los Angeles, CA', cycle: '60' },
  },
]
