/**
 * jsdom kennt `<dialog>`, aber weder `showModal()` noch `close()`. Diese Ersatzfunktionen setzen das
 * Attribut `open` und melden `close`, damit die modalen Fenster in den Tests wie im Browser laufen.
 */
HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement): void {
  this.setAttribute('open', '');
};

HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement): void {
  if (this.hasAttribute('open')) {
    this.removeAttribute('open');
    this.dispatchEvent(new Event('close'));
  }
};
