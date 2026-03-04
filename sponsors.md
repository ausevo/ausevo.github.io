---
layout: page
title: Conference Sponsors
subtitle: Supporting AES 2026
---

<div class="sponsor-cta-box">
  <h2>Support AES {{ site.data.sponsors.year }}</h2>
  <p>Sponsorship of AES directly subsidises registration costs for students and early-career researchers, making our annual conference more accessible to the next generation of evolutionary biologists.</p>
  <div class="sponsor-cta-box__actions">
    <a href="mailto:{{ site.data.sponsors.contact_email }}" class="btn btn--coral">
      <i class="fa-solid fa-envelope" aria-hidden="true"></i> Get in touch
    </a>
    {% if site.data.sponsors.prospectus_url and site.data.sponsors.prospectus_url != "" %}
    <a href="{{ site.data.sponsors.prospectus_url }}" class="btn btn--outline" target="_blank" rel="noopener">
      <i class="fa-solid fa-file-pdf" aria-hidden="true"></i> Download Prospectus
    </a>
    {% endif %}
  </div>
</div>

## Sponsorship Tiers

{% for tier in site.data.sponsors.tiers %}
<div class="sponsor-tier">
  <div class="sponsor-tier__header sponsor-tier__header--{{ tier.slug }}">
    {% if tier.slug == "platinum" %}<i class="fa-solid fa-gem" aria-hidden="true"></i>
    {% elsif tier.slug == "gold" %}<i class="fa-solid fa-medal" aria-hidden="true"></i>
    {% elsif tier.slug == "silver" %}<i class="fa-solid fa-award" aria-hidden="true"></i>
    {% else %}<i class="fa-solid fa-star" aria-hidden="true"></i>
    {% endif %}
    {{ tier.name }}
  </div>
  {% if site.data.sponsors.show_tier_descriptions %}
  <p class="sponsor-tier__desc">{{ tier.description }}</p>
  {% endif %}
  <div class="sponsor-grid sponsor-grid--{{ tier.slug }}">
    {% if tier.sponsors and tier.sponsors.size > 0 %}
      {% for sponsor in tier.sponsors %}
      <a href="{{ sponsor.url }}" class="sponsor-card" target="_blank" rel="noopener" aria-label="{{ sponsor.name }}">
        {% if sponsor.logo %}
        <img src="{{ sponsor.logo }}" alt="{{ sponsor.name }}" loading="lazy">
        {% else %}
        <span class="sponsor-card__name">{{ sponsor.name }}</span>
        {% endif %}
      </a>
      {% endfor %}
    {% else %}
    <div class="sponsor-card sponsor-placeholder">
      <div>
        <i class="fa-regular fa-handshake" aria-hidden="true"></i>
        <span>Become our {{ tier.name }} Sponsor</span>
      </div>
    </div>
    {% endif %}
  </div>
</div>
{% endfor %}

---

### Past sponsors

We are grateful to the institutions and organisations that have supported past AES conferences. Sponsorship directly subsidises registration costs for students and early career researchers.
