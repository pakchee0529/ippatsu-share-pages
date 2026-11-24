export function attachCamera(button, onPhoto) {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*';
  input.setAttribute('capture', 'environment');
  input.hidden = true;
  button.after(input);
  button.addEventListener('click', () => input.click());
  input.addEventListener('change', () => {
    const picture = input.files[0];
    if (picture) onPhoto(picture);
    input.value = '';
  });
}
