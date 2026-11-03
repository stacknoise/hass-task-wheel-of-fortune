export { ApiClient } from './client.ts';
export type { Unsubscribe } from './client.ts';
export type {
  CollectionDelta,
  Collections,
  Delta,
  HassApi,
  HassConnection,
  Settings,
  Snapshot,
  WireObject,
} from './types.ts';
export type {
  AbsenceWire,
  FrequencyWire,
  PersonWire,
  ScheduleWire,
  TaskWire,
  TriggerWire,
} from './config-types.ts';
export { failureFor, parseFailure } from './errors.ts';
export type { ApiFailure } from './errors.ts';
export { personsOf, schedulesOf, tasksOf } from './collections.ts';
