Local copies of the register's sources live here.

This folder is filled by:   python3 tools/archive.py

Layout:
  archive/<RECORD-ID>/<YYYY-MM-DD>/official.html|pdf     the page at the official URL
  archive/<RECORD-ID>/<YYYY-MM-DD>/document-1.pdf        PDFs linked from that page (usually the legal text)
  archive/<RECORD-ID>/<YYYY-MM-DD>/secondary.html|pdf    the secondary source
  archive/<RECORD-ID>/<YYYY-MM-DD>/SHA256SUMS            hashes; check with: sha256sum -c SHA256SUMS
  archive/manifest.json                                  every record's local-copy status, files and hashes
  archive/runs.jsonl                                     one line per archiver run
  archive/needs-attention.txt                            records that still need a human decision; rewritten after every run

Do not edit files here by hand: `python3 tools/archive.py --verify` flags any file
whose hash no longer matches what was recorded when it was downloaded.
