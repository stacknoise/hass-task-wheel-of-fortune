/** Design-Tokens: eigene Eigenschaften, jeweils auf eine Variable von Home Assistant gemappt. */

export const TOKENS = {
  '--tw-color-primary': 'var(--primary-color, #03a9f4)',
  '--tw-color-text': 'var(--primary-text-color, #212121)',
  '--tw-color-text-muted': 'var(--secondary-text-color, #727272)',
  '--tw-color-surface': 'var(--card-background-color, #ffffff)',
  '--tw-color-background': 'var(--primary-background-color, #fafafa)',
  '--tw-color-divider': 'var(--divider-color, #e0e0e0)',
  '--tw-color-error': 'var(--error-color, #db4437)',
  '--tw-color-stage': '#10243a',
  '--tw-color-stage-text': '#ffffff',
  '--tw-color-stage-muted': '#9fc4e4',
  '--tw-color-rim': '#f5c542',
  '--tw-space-s': '8px',
  '--tw-space-m': '16px',
  '--tw-space-l': '24px',
  '--tw-radius': 'var(--ha-card-border-radius, 12px)',
  '--tw-duration': '200ms',
} as const;
