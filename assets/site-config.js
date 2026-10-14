/* Settings for where the app is hosted. Empty values mean: served from this folder.
   tools/publish_hf.py writes its own copy of this file into the Hugging Face Space. */
window.SITE_CONFIG = {
  archiveBase: "",        /* prefix for links to stored source files, e.g. a dataset's /blob/main/ URL */
  archiveExcluded: [],    /* stored files that are not published at archiveBase (shown without a link) */
  datasetUrl: "",         /* where the data can be downloaded */
  archiveDatasetUrl: "",  /* where the stored source documents can be downloaded */
  repoUrl: ""             /* the GitHub repository for issues; empty means kelkalot/every-ai-policy-ever */
};
