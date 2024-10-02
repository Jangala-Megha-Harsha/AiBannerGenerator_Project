document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generate-btn');
    const templateSelect = document.getElementById('template-select');
    const themeInput = document.getElementById('theme-input');
    const productInput = document.getElementById('product-input');
    const offerInput = document.getElementById('offer-input');
    const bannerImage = document.getElementById('banner-image');
    const bannerText = document.getElementById('banner-text');

    generateBtn.addEventListener('click', function() {
        const templateId = templateSelect.value;
        const theme = themeInput.value;
        const product = productInput.value;
        const offer = offerInput.value;
        console.log(1);
        fetch('/generate-banner', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                template_id: templateId,
                theme: theme,
                product: product,
                offer: offer
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.banner_url) {
                bannerImage.src = data.banner_url;
                bannerImage.style.display = 'block';
                bannerText.textContent = `Headline: ${data.headline}\nSubheadline: ${data.subheadline}`;
            } else {
                console.error('Error generating banner:', data.error);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    });
});