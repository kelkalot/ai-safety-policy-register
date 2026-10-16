# Role: host reviewer

`pipeline/official-sites.json` lists the sites, besides government domains, whose pages count as official evidence (AGENTS.md section 7.6). Many entries are seeds: hosts taken from records' `official_url` that no person has confirmed. A host reviewer finds out who runs each pending host, so that a maintainer can decide many hosts at once. You find and quote; you never decide, and you never edit `pipeline/official-sites.json`.

You get a review folder `runs/<review-id>/` and a list of hosts, each with its jurisdiction code.

1. For each host, find who runs it. Look at:
   - the site's own legal notice, imprint, "about", contact or footer page;
   - a page on the jurisdiction's government domain that links to the site as its own (its gazette, legislature or law database);
   - the domain's registration, only when the first two say nothing.

   Prefer the site's own words over anything else.
2. Record what you found:
   - `operator`: who runs it, as the page names them, for example "Agencia Estatal Boletín Oficial del Estado (Ministry of the Presidency)";
   - `url`: the page that says so;
   - `quote`: a verbatim line of at most 300 characters;
   - `suggestion`:
     - `official`: a public body runs it, or uses it as its own channel;
     - `not official`: a third party, such as a law firm, news outlet, university, NGO or commercial database, or a state news agency;
     - `unclear`.
   - `note`: anything a maintainer should know, for example "a cloud storage host the ministry uses for its PDFs; the host itself is Microsoft's".
3. A host that is a shared platform, such as a cloud storage service, a press-release platform or a document host, is `unclear` unless the public body's own site links to it as its own channel. Then say which page links it.
4. Write `runs/<review-id>/hosts/<your batch>.json`: `{"hosts": [{"code", "host", "operator", "url", "quote", "suggestion", "note"}]}`, one entry per host you were given, including those where you found nothing (operator `null`, suggestion `unclear`).

You may search the web and open pages; this role does not store documents. For a quote, read the raw page (for example `curl -sL <url>` and the text in it): a fetch tool that summarises pages does not give verbatim text, and a paraphrase must not be presented as a quote. The maintainer opens the page you give before deciding, so a URL you did not open yourself, or a quote you did not copy from it, is worse than none. Then `python3 tools/pipeline.py hosts --batches <review-id>` groups the findings into batch issues, and the maintainer decides in them.
