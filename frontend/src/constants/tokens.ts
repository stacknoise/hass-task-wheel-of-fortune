/** Design-Tokens: eigene Eigenschaften, jeweils auf eine Variable von Home Assistant gemappt. */

export const TOKENS = {
  '--tw-color-primary': 'var(--primary-color, #03a9f4)',
  '--tw-color-on-primary': 'var(--text-primary-color, #ffffff)',
  '--tw-color-text': 'var(--primary-text-color, #212121)',
  '--tw-color-text-muted': 'var(--secondary-text-color, #727272)',
  '--tw-color-surface': 'var(--card-background-color, #ffffff)',
  '--tw-color-background': 'var(--primary-background-color, #fafafa)',
  '--tw-color-divider': 'var(--divider-color, #e0e0e0)',
  '--tw-color-error': 'var(--error-color, #db4437)',
  '--tw-color-success': 'var(--success-color, #43a047)',
  '--tw-color-warning': 'var(--warning-color, #ffa600)',
  '--tw-color-info': 'var(--info-color, #039be5)',
  '--tw-color-neutral': 'var(--disabled-color, #9e9e9e)',
  '--tw-color-fill': 'var(--secondary-background-color, #e5e5e5)',
  '--tw-color-rim': '#f5c542',
  '--tw-space-s': '8px',
  '--tw-space-m': '16px',
  '--tw-space-l': '24px',
  '--tw-radius': 'var(--ha-card-border-radius, 12px)',
  '--tw-duration': '200ms',
} as const;
