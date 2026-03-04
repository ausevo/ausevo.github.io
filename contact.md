---
title: "AES Executive Committee"
subtitle: Contact
layout: page
---

## Contact us

**Email:** [ausevolutionsociety@gmail.com](mailto:ausevolutionsociety@gmail.com)

We are also active on [Bluesky @austevolsoc](https://bsky.app/profile/austevolsoc.bsky.social), [Facebook](https://www.facebook.com/ausevosoc), and [X / Twitter @AustEvolSoc](https://twitter.com/austevolsoc).

---

## The AES {{ site.data.exec.year }} Executive Committee

{% for role in site.data.exec.roles %}
### {{ role.title }}

<div class="exec-grid">
{% for member in role.members %}
<div class="exec-card">
  {% if member.photo %}
  <img class="exec-card__avatar" src="{{ member.photo }}" alt="{{ member.name }}">
  {% else %}
  <div class="exec-card__avatar"><i class="fa-solid fa-circle-user" aria-hidden="true"></i></div>
  {% endif %}
  {% if member.url %}
  <p class="exec-card__name"><a href="{{ member.url }}">{{ member.name }}</a></p>
  {% else %}
  <p class="exec-card__name">{{ member.name }}</p>
  {% endif %}
  <p class="exec-card__inst">{{ member.institution }}</p>
</div>
{% endfor %}
</div>
{% endfor %}
