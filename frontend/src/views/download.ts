import { REVOKE_DELAY_MS } from '../constants/index.ts';

/** Bietet den Text im Browser als Datei zum Speichern an. */
export function downloadText(fileName: string, content: string, mime: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: mime }));
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  // Im Dokument und mit verzögerter Freigabe: Safari, Firefox und die Companion-App lesen die Adresse erst nach dem Klick.
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => {
    URL.revokeObjectURL(url);
  }, REVOKE_DELAY_MS);
}
