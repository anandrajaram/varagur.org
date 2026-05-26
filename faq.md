---
layout: page
title: "Frequently Asked Questions"
permalink: /faq/
description: "Answers to common questions about Varagur, Sri Venkatesa Perumal Kovil, Sri Narayana Theerthar, the Krishna Leela Tharangini, the Uriyadi festival, and how to visit."
image: /assets/images/index/gopuram-final.jpg
---

This page collects the most common questions we receive about Varagur and its temples. Each section links back to the page on this site where the topic is covered in more depth.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {%- assign sections = "village,temple,saint,tharangini,uriyadi,visit" | split: "," -%}
    {%- for key in sections -%}
    {%- assign entries = site.data.faq[key] -%}
    {%- for entry in entries -%}
    {
      "@type": "Question",
      "name": {{ entry.q | jsonify }},
      "acceptedAnswer": {
        "@type": "Answer",
        "text": {{ entry.a | jsonify }}
      }
    }{%- unless forloop.last and forloop.parentloop.last %},{% endunless -%}
    {%- endfor -%}
    {%- endfor -%}
  ]
}
</script>

## About Varagur village

[More on the Sthala Puranam &rsaquo;](/home/about/)

{% for entry in site.data.faq.village %}
### {{ entry.q }}

{{ entry.a | markdownify }}
{% endfor %}

## Sri Venkatesa Perumal Kovil

[More on the temple &rsaquo;](/home/sri-venkatesa-perumal-kovil/)

{% for entry in site.data.faq.temple %}
### {{ entry.q }}

{{ entry.a | markdownify }}
{% endfor %}

## Sri Narayana Theerthar

[More on the saint &rsaquo;](/home/sri-narayana-theerthar/)

{% for entry in site.data.faq.saint %}
### {{ entry.q }}

{{ entry.a | markdownify }}
{% endfor %}

## Krishna Leela Tharangini

[More on the Tharangini &rsaquo;](/home/krishna-leela-tharangini/)

{% for entry in site.data.faq.tharangini %}
### {{ entry.q }}

{{ entry.a | markdownify }}
{% endfor %}

## The Uriyadi festival

[More on Uriyadi &rsaquo;](/uriyadi/)

{% for entry in site.data.faq.uriyadi %}
### {{ entry.q }}

{{ entry.a | markdownify }}
{% endfor %}

## Visiting Varagur

[Visitor guide &rsaquo;](/visit/)

{% for entry in site.data.faq.visit %}
### {{ entry.q }}

{{ entry.a | markdownify }}
{% endfor %}
