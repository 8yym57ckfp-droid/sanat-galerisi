document.addEventListener('change', function (event) {
  const input = event.target.closest('input[type="file"][name="image"]');
  if (!input || !input.files || !input.files[0]) return;
  const preview = document.querySelector('[data-preview]');
  if (!preview) return;
  const image = preview.querySelector('img');
  image.src = URL.createObjectURL(input.files[0]);
  preview.classList.add('has-image');
});

document.addEventListener('click', function (event) {
  const button = event.target.closest('[data-carousel]');
  if (!button) return;
  const carousel = button.closest('.carousel');
  const track = carousel && carousel.querySelector('.carousel-track');
  if (!track) return;
  const card = track.querySelector('.product-card');
  const distance = card ? card.getBoundingClientRect().width + 18 : 280;
  track.scrollBy({ left: button.dataset.carousel === 'next' ? distance : -distance, behavior: 'smooth' });
});
