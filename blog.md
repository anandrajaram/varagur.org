---
layout: page
title: "Blog"
permalink: /blog/
---

<ul class="post-list">
{% for post in site.posts %}
  <li>
    <h2><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h2>
    <time class="post-date" datetime="{{ post.date | date_to_xmlschema }}">{{ post.date | date: "%B %-d, %Y" }}</time>
    {% if post.excerpt %}<div class="post-excerpt">{{ post.excerpt }}</div>{% endif %}
  </li>
{% endfor %}
</ul>
