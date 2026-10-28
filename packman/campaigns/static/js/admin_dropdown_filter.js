"use strict";
{
  const $ = django.jQuery;

  $(function () {
    $("select[data-dropdown-filter]").each(function () {
      const select = $(this);
      if (this.hasAttribute("data-searchable")) {
        select.select2({ theme: "admin-autocomplete", width: "100%" });
        select.next(".select2-container").find("[role=combobox]")
          .removeAttr("aria-labelledby").attr("aria-label", select.attr("aria-label"));
      }
      select.on("change", function () {
        window.location.assign(this.value);
      });
    });
  });
}
