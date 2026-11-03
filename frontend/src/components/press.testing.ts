type UpdatingElement = HTMLElement & { updateComplete: Promise<boolean> };

/** Knöpfe eines Bausteins samt seines Rückfrage-Dialogs (der Dialog steht im eigenen Shadow-DOM). */
export function innerButtons(host: Element): HTMLButtonElement[] {
  const dialog = host.shadowRoot?.querySelector('tw-confirm-dialog');
  return [
    ...(host.shadowRoot?.querySelectorAll('button') ?? []),
    ...(dialog?.shadowRoot?.querySelectorAll('button') ?? []),
  ];
}

/** Drückt den letzten Knopf des Bausteins mit dem Text `label` und wartet auf das Rendern. */
export async function press(host: Element, label: string): Promise<void> {
  innerButtons(host)
    .filter((button) => button.textContent.includes(label))
    .at(-1)
    ?.click();
  await (host as UpdatingElement).updateComplete;
  await (host.shadowRoot?.querySelector('tw-confirm-dialog') as UpdatingElement | null)
    ?.updateComplete;
}
