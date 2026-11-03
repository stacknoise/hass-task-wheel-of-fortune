import type { de } from './de.ts';

export const en: Record<keyof typeof de, string> = {
  'panel.title': 'Task Wheel of Fortune',
  'panel.loading': 'Loading data …',
  'panel.error': 'The data could not be loaded.',
  'panel.nav': 'Sections',
  'tab.overview': 'Overview',
  'tab.draw': 'Draw',
  'tab.tasks': 'Tasks',
  'tab.persons': 'People',
  'tab.schedules': 'Schedules',
  'tab.history': 'History',
  'tab.statistics': 'Statistics',
  'stat.persons': 'People',
  'stat.tasks': 'Tasks',
  'stat.schedules': 'Schedules',
  'stat.assignments': 'Open assignments',
  'stat.panel_rounds': 'Open draws',
  'view.soon': 'This section will follow in an upcoming work package.',
};
